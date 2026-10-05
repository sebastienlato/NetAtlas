"""Evaluation validates its own denominators and independently authored oracles."""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from netatlas.derivations.engine import canonical, digest
from netatlas.evaluation.__main__ import backpressure, disposable, main
from netatlas.evaluation.corpus import load_corpus
from netatlas.evaluation.loopback import trial as loopback_trial
from netatlas.evaluation.performance import distribution, expected, trial
from netatlas.evaluation.scenarios import coverage, functional
from netatlas.evaluation.scoring import evaluate, score, wilson
from netatlas.storage.database import local_engine

AT = datetime(2026, 10, 5, 12, tzinfo=UTC)


def test_multilabel_denominators_abstention_unlabelled_and_false_positives() -> None:
    result = score(
        [{"a", "b"}, {"a"}, set(), None],
        [{"a"}, {"c"}, {"a"}, {"b"}],
        {"a", "b", "c", "unsupported"},
    )
    assert result["labelled_sources"] == 3
    assert result["excluded_unlabelled_sources"] == 1
    assert result["predictions_on_unlabelled_sources"] == 1
    a = result["classes"]["a"]
    assert (a["tp"], a["fp"], a["fn"], a["precision"], a["recall"]) == (1, 1, 1, 0.5, 0.5)
    assert result["classes"]["b"]["precision"] is None
    assert result["classes"]["b"]["recall"] == 0
    assert result["classes"]["unsupported"]["recall"] is None
    assert score([{"a"}], [set()], set())["unknown_output_sources"] == 1
    with pytest.raises(ValueError):
        score([], [set()], set())
    assert wilson(0, 0) is None
    interval = wilson(1, 1)
    assert interval is not None and 0.20 < interval[0] < 0.21 and interval[1] == 1


def test_corpus_retains_spoofs_unknowns_unsupported_and_multiple_without_tuning() -> None:
    corpus = load_corpus()
    original = canonical(corpus)
    result = evaluate(corpus, AT)
    assert result == evaluate(corpus, AT)
    assert canonical(corpus) == original
    assert len(result["rows"]) == 30
    classes = result["product_assertions"]["classes"]
    assert {k: (v["tp"], v["fp"], v["fn"]) for k, v in classes.items()} == {
        "nginx": (6, 0, 1),
        "OpenSSH": (3, 0, 1),
        "Postfix": (1, 0, 0),
        "Apache": (0, 0, 1),
    }
    assert result["product_assertions"]["excluded_unlabelled_sources"] == 1
    roles = result["category_scenarios"]["classes"]
    assert len(roles) == 11
    assert roles["iot"]["support"] == 3 and roles["iot"]["recall"] == 0
    assert roles["web_server"]["fp"] == 1
    assert roles["ssh_server"]["fp"] == 1
    rows = {r["case"]: r for r in result["rows"]}
    assert rows["duplicate-marker"]["candidate_records"] == 2
    assert rows["duplicate-marker"]["products"] == ["nginx"]
    assert rows["two-products"]["roles"] == ["ssh_server", "web_server"]
    assert rows["spoof-nginx"]["identity_mismatch_if_misinterpreted"]
    assert not rows["spoof-nginx"]["assertion_mismatch"]
    # Mutation of truth affects metrics, never production predictions or fixture inputs.
    changed = corpus.model_copy(
        update={"cases": (corpus.cases[0].model_copy(update={"products": ()}), *corpus.cases[1:])}
    )
    mutated = evaluate(changed, AT)
    assert mutated["product_assertions"]["classes"]["nginx"]["fp"] == 1
    assert result["rows"][0]["result_sha256"] == mutated["rows"][0]["result_sha256"]
    assert digest(canonical(corpus)) != digest(canonical(changed))


def test_independent_benchmark_page_oracle_and_tail_definition() -> None:
    assert expected("all_history")[:2] == (128, 352)
    assert expected("network")[:2] == (16, 16)
    assert expected("fresh")[:2] == (96, 96)
    assert expected("text_rare")[:2] == (2, 2)
    assert len(expected("all_current")[2]) == 50
    assert distribution([1, 2, 3, 4])["p95_nearest_rank"] == 4
    assert distribution([1, 2, 3, 4])["median"] == 2.5
    with pytest.raises(ValueError):
        expected("unlisted")


def test_coverage_reports_seed_bias_exclusions_and_negative_refresh() -> None:
    result = coverage(AT)
    assert result == coverage(AT)
    assert result["baseline"]["ipv6_seedless_routed_regions"] == 1
    assert result["exclusions"]["scheduled"] == 11
    assert result["refresh_boundary"]["latest_outcome"] == "timeout"
    assert len({r["input_sha256"] for r in result["trials"]}) == 3
    assert all(sum(r["shards"]) == 7 for r in result["trials"])


@pytest.mark.parametrize("destination", ["outside.json", "data/existing.json", "data/link.json"])
def test_cli_rejects_unsafe_or_existing_output_before_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    destination: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir(mode=0o700)
    (tmp_path / "data/existing.json").write_text("keep")
    (tmp_path / "data/link.json").symlink_to(tmp_path / "absent")

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("experiment should not start")

    monkeypatch.setattr("netatlas.evaluation.__main__.run", forbidden)
    monkeypatch.setattr(
        sys, "argv", ["evaluation", "--synthetic", "--at", AT.isoformat(), "--output", destination]
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert (tmp_path / "data/existing.json").read_text() == "keep"


def test_cli_private_publication_and_generic_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluation", "--synthetic", "--at", AT.isoformat(), "--output", "data/report.json"],
    )
    monkeypatch.setattr("netatlas.evaluation.__main__.run", lambda *args: {"workload": "fixture"})
    main()
    output = tmp_path / "data/report.json"
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(output.read_bytes()) == {"workload": "fixture"}
    output.unlink()

    def fail(*args: Any) -> None:
        raise ValueError("private exception sentinel")

    monkeypatch.setattr("netatlas.evaluation.__main__.run", fail)
    with pytest.raises(SystemExit):
        main()
    assert "sentinel" not in capsys.readouterr().err
    assert not output.exists()


def test_complete_disposable_evaluation_and_failure_cleanup(tmp_path: Path) -> None:
    if os.environ.get("NETATLAS_TEST_DB") != "1":
        pytest.skip("requires local Compose; run make check-db")
    admin = local_engine(Path("data/storage"))

    def inventory() -> set[str]:
        with admin.connect() as conn:
            return set(
                conn.execute(
                    text(
                        "SELECT datname FROM pg_database WHERE datname LIKE 'netatlas_test_eval_%'"
                    )
                ).scalars()
            )

    before = inventory()
    with admin.connect() as conn:
        at: datetime = conn.execute(
            text("SELECT clock_timestamp() - interval '30 seconds'")
        ).scalar_one()
        owner_before: int = conn.execute(text("SELECT count(*) FROM observations")).scalar_one()
    try:
        with disposable(admin) as pipeline:
            result = functional(pipeline, at)
            assert result["queries"]["attempt"]["sources"] == 6
            assert result["age_seconds"]["evidence"][-1] == 200000
        with disposable(admin) as pipeline:
            assert backpressure(pipeline, at)["acknowledged_during_fault"] == 0
        with disposable(admin) as pipeline:
            result = trial(pipeline, at, 2)
            assert [c["sources"] for c in result["footprint"]] == [0, 96, 384]
            assert result["reads"]["all_history"]["sources"] == 352
            assert result["verified"]["observations"] == 384
        with disposable(admin) as pipeline:
            measured = asyncio.run(loopback_trial(pipeline, tmp_path / "spool"))
            assert measured["connections"] == measured["completed"] == 4
        with pytest.raises(RuntimeError), disposable(admin):
            raise RuntimeError("authored cleanup drill")
        assert inventory() == before
        with admin.connect() as conn:
            assert (
                conn.execute(text("SELECT count(*) FROM observations")).scalar_one() == owner_before
            )
    finally:
        admin.dispose()
