"""Independent authored coverage truth plus real PostgreSQL scheduling failure acceptance."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text
from test_control import (
    authority,
    boot,
    claim,
    config,
    delivery,
    expire_lease,
    identity,
    permit,
    queue,
    register,
)
from test_storage import observation, scalar

from netatlas.control.coordinator import Coordinator
from netatlas.control.models import Claim, ControlError, Heartbeat
from netatlas.derivations.engine import canonical, digest
from netatlas.observation import Observation
from netatlas.scheduler.cli import main, read_input
from netatlas.scheduler.models import PlanningInput, Source
from netatlas.scheduler.planner import plan
from netatlas.scheduler.service import enqueue, report, snapshot
from netatlas.storage.blobs import BlobStore
from netatlas.storage.database import migrate, transaction
from netatlas.storage.pipeline import Pipeline

pytest_plugins = ["test_storage"]
AT = datetime(2026, 10, 4, 12, tzinfo=UTC)


def request(*, lab: bool = False, at: datetime = AT, **policy: Any) -> PlanningInput:
    regions = [
        ("192.0.2.0/29", "routed"),
        ("198.51.100.0/30", "routed"),
        ("203.0.113.0/31", "unrouted"),
        ("203.0.113.4/30", "unknown"),
        ("2001:db8:1::/48", "routed"),
        ("2001:db8:2::/48", "routed"),
        ("2001:db8:3::/48", "unknown"),
    ]
    seeds = ["2001:db8:1::1", "2001:db8:1::2", "2001:db8:3::1"]
    if lab:
        regions, seeds = [("127.0.0.1/32", "routed"), ("::1/128", "routed")], ["::1"]
    return PlanningInput.model_validate(
        {
            "schema_version": 1,
            "lab_loopback": lab,
            "at": at,
            "settings": config(),
            "policy": policy,
            "universe": {
                "id": "authored-coverage",
                "version": "1",
                "valid_from": at - timedelta(days=1),
                "expires_at": at + timedelta(days=1),
                "origins": [
                    {
                        "id": "fixture",
                        "version": "1",
                        "content_sha256": "a" * 64,
                        "attribution": "Authored test universe; not routing evidence",
                        "license": "repository terms",
                    }
                ],
                "regions": [
                    {"network": n, "state": state, "origin_id": "fixture"} for n, state in regions
                ],
                "seeds": [{"address": address, "origin_id": "fixture"} for address in seeds],
                "ports": [12345],
            },
        }
    )


def change(r: PlanningInput, **values: Any) -> PlanningInput:
    return PlanningInput.model_validate(r.model_dump() | values)


def summary(source: Observation) -> Source:
    return Source(
        endpoint=source.endpoint,
        observation_id=source.observation_id,
        source_sha256=digest(canonical(source)),
        started_at=source.started_at,
        finished_at=source.finished_at,
        outcome=source.outcome,
    )


def test_authored_truth_denominators_ipv6_seeds_and_disjoint_shards() -> None:
    r = request(shards=3)
    p = plan(r)
    truth = {
        *(f"192.0.2.{i}" for i in range(8)),
        *(f"198.51.100.{i}" for i in range(4)),
        "2001:db8:1::1",
        "2001:db8:1::2",
    }
    assert {str(e.endpoint.address) for e in p.entries} == truth
    assert p.counts == {
        "blocked": 0,
        "candidate_endpoints": 14,
        "coverage": 14,
        "eligible": 14,
        "excluded": 0,
        "expired_history": 0,
        "fresh": 0,
        "ipv4_routed_addresses": 12,
        "ipv4_unknown_addresses": 4,
        "ipv4_unrouted_addresses": 2,
        "ipv6_nonrouted_seeds": 1,
        "ipv6_routed_regions": 2,
        "ipv6_routed_seeds": 2,
        "ipv6_seedless_routed_regions": 1,
        "ipv6_unknown_regions": 1,
        "ipv6_unrouted_regions": 0,
        "queue_deferred": 0,
        "refresh": 0,
        "sampled_out": 0,
        "scheduled": 14,
    }
    partitions = [{e.identity for e in p.entries if e.shard == n} for n in range(3)]
    assert sum(map(len, partitions)) == len(set.union(*partitions)) == 14
    assert canonical(p) == canonical(plan(PlanningInput.model_validate_json(r.model_dump_json())))
    assert all(e.seed_origin_id == "fixture" for e in p.entries if e.endpoint.address.version == 6)


def test_prefix_fairness_sampling_and_rotating_bounded_queue() -> None:
    p = plan(request(sample_per_prefix=3, queue_size=7))
    assert Counter(e.prefix for e in p.entries[:6]) == {
        "192.0.2.0/24": 2,
        "198.51.100.0/24": 2,
        "2001:db8:1::/48": 2,
    }
    assert p.counts["sampled_out"] == 6
    assert p.counts["queue_deferred"] == 1
    assert len(p.entries) == 7
    # Even a one-entry queue visits all three prefixes over three explicit rounds.
    assert len({plan(request(queue_size=1, round=n)).entries[0].prefix for n in range(3)}) == 3
    assert plan(request(seed=7)) != plan(request(seed=8))


def test_optouts_allowlists_blocked_and_unknown_never_become_candidates() -> None:
    r = request()
    r = change(
        r,
        settings=config(exclusion_cidrs=["192.0.2.0/31"], opt_out_cidrs=["2001:db8:1::1/128"]),
        suppressions=["198.51.100.0/31"],
        blocked=[{"address": "192.0.2.2", "port": 12345}],
    )
    p = plan(r)
    assert p.counts["excluded"] == 5
    assert p.counts["blocked"] == 1
    assert p.counts["scheduled"] == 8
    narrowed = plan(
        change(r, settings=config(allow_cidrs=["192.0.2.0/24"], opt_out_cidrs=["192.0.2.0/31"]))
    )
    assert narrowed.counts["scheduled"] == 5


def test_refresh_latest_negative_priority_expiration_and_new_identity() -> None:
    r = request()
    endpoint = {"address": "192.0.2.1", "port": 12345}
    old = {
        "endpoint": endpoint,
        "observation_id": UUID(int=1),
        "source_sha256": "b" * 64,
        "started_at": AT - timedelta(days=5, seconds=1),
        "finished_at": AT - timedelta(days=5),
        "outcome": "open",
    }
    negative = old | {
        "observation_id": UUID(int=2),
        "source_sha256": "c" * 64,
        "started_at": AT - timedelta(days=3, seconds=1),
        "finished_at": AT - timedelta(days=3),
        "outcome": "timeout",
    }
    r = change(r, history=[negative, old])
    selected = next(
        e
        for e in plan(r).entries
        if e.endpoint.address == Source.model_validate(old).endpoint.address
    )
    assert selected.kind == "refresh" and selected.previous is not None
    assert selected.previous.observation_id == UUID(int=2)
    assert selected.due_at == AT - timedelta(days=1)
    assert next(e for e in plan(r).entries if e.prefix == "192.0.2.0/24") == selected
    later = next(e for e in plan(change(r, at=AT + timedelta(seconds=1))).entries if e.previous)
    assert later.identity != selected.identity
    # Latest refusal is fresh for seven days: no older-open fallback.
    assert plan(change(r, history=[old, negative | {"outcome": "closed"}])).counts["fresh"] == 1
    expired = old | {
        "started_at": AT - timedelta(days=30, seconds=1),
        "finished_at": AT - timedelta(days=30),
    }
    p = plan(change(r, history=[expired]))
    assert p.counts["expired_history"] == 1 and p.counts["refresh"] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        {
            "regions": [
                {"network": "192.0.2.0/24", "state": "routed", "origin_id": "fixture"},
                {"network": "192.0.2.0/25", "state": "unknown", "origin_id": "fixture"},
            ]
        },
        {"regions": [{"network": "0.0.0.0/0", "state": "routed", "origin_id": "fixture"}]},
        {"seeds": [{"address": "2001:db8:9::1", "origin_id": "fixture"}]},
        {"seeds": [{"address": "2001:db8:1::1%en0", "origin_id": "fixture"}]},
        {"seeds": [{"address": "2001:db8:1::1", "origin_id": "missing"}]},
        {"ports": [80, 80]},
    ],
)
def test_invalid_universe_fails_before_expansion(mutation: dict[str, Any]) -> None:
    r = request()
    with pytest.raises(ValueError):
        change(r, universe=r.universe.model_dump() | mutation)


def test_huge_ipv6_region_is_seed_only_and_expired_universe_rejected() -> None:
    r = request()
    r = change(
        r,
        universe=r.universe.model_dump()
        | {"regions": [{"network": "2001:db8::/32", "state": "routed", "origin_id": "fixture"}]},
    )
    assert len(plan(r).entries) == 3
    with pytest.raises(ValueError):
        plan(change(r, at=r.universe.expires_at))
    with pytest.raises(ValueError):
        change(r, policy={"queue_size": 129})


def test_private_cli_defaults_no_storage_no_clobber_and_input_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: Any,
) -> None:
    monkeypatch.chdir(tmp_path)
    raw = tmp_path / "request.json"
    raw.write_bytes(canonical(request()))

    def forbidden(*args: Any) -> Any:
        raise AssertionError("offline plan opened storage")

    monkeypatch.setattr("netatlas.scheduler.cli.local_engine", forbidden)
    assert main(["plan", "--input", str(raw), "--output", "data/plan.json"]) == 0
    assert (tmp_path / "data/plan.json").stat().st_mode & 0o777 == 0o600
    assert main(["enqueue", "--input", str(raw)]) == 0
    assert main(["plan", "--input", str(raw), "--output", "data/plan.json"]) == 2
    assert "192.0.2" not in capsys.readouterr().out
    raw.write_bytes(b"x" * (1048576 + 1))
    with pytest.raises(ValueError):
        read_input(raw)
    raw.write_text('{"schema_version":1,"schema_version":1}')
    with pytest.raises(ValueError):
        read_input(raw)


def lab_request(**policy: Any) -> PlanningInput:
    return request(lab=True, at=datetime.now(UTC) - timedelta(seconds=1), **policy)


def submit(c: Coordinator, r: PlanningInput) -> UUID:
    return enqueue(c, r, measure=True, synthetic=True)


def test_execution_boundary_order_replay_global_budget_and_restart(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    with pytest.raises(ValueError):
        submit(c, request(at=datetime.now(UTC)))
    r = lab_request()
    campaign = submit(c, r)
    assert submit(c, r) == campaign
    assert scalar(pipeline, "SELECT count(*) FROM control_jobs") == 2
    a, b = boot(), boot()
    register(c, a)
    register(c, b)
    first, second = claim(c, a), claim(c, b)
    assert [first.endpoint, second.endpoint] == [e.endpoint for e in plan(r).entries]
    assert permit(c, a, first).status == "granted"
    assert permit(Coordinator(pipeline), b, second).status == "wait"
    c.exchange(delivery(a, first))
    counts = report(c, campaign)["execution"]
    assert counts == {
        "scheduled": 2,
        "admitted": 1,
        "permits_issued": 1,
        "measured": 1,
        "incomplete_or_uncertain": 0,
        "not_admitted": 0,
        "queued": 0,
        "active": 1,
        "refreshed": 0,
        "retained": 1,
    }
    c.cancel(campaign)
    assert submit(c, r) == campaign
    assert c.status() == {"cancelled": 2}


def test_global_stop_reopen_never_revives_jobs_or_authority(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    r = lab_request()
    campaign = submit(c, r)
    b = boot()
    register(c, b)
    lease = claim(c, b)
    permit(c, b, lease)
    c.stop()
    assert report(c, campaign)["global_stopped"] is True
    with pytest.raises(ControlError):
        c.exchange(Heartbeat.model_validate(authority(b, lease) | {"action": "heartbeat"}))
    with pytest.raises(ControlError):
        queue(Coordinator(pipeline), 12346)
    c.allow_new_work()
    assert c.status() == {"cancelled": 2}
    with pytest.raises(ControlError):
        permit(c, b, lease, 2)
    assert submit(c, r) == campaign
    with pytest.raises(ControlError, match="unresolved_attempt"):
        submit(c, change(r, at=datetime.now(UTC) - timedelta(milliseconds=500)))
    assert queue(c, 12346, settings=config(max_concurrency=1))
    assert c.exchange(Claim.model_validate(identity(b) | {"action": "claim"})).status == "wait"


def test_suppression_atomic_revoke_snapshot_and_changed_exclusions(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    r = lab_request()
    campaign = submit(c, r)
    b = boot()
    register(c, b)
    lease = claim(c, b)
    assert permit(c, b, lease).status == "granted"
    pipeline.maintain(suppress=str(lease.endpoint.address))
    assert scalar(pipeline, "SELECT count(*) FROM control_jobs WHERE state='cancelled'") == 1
    with pytest.raises(ControlError):
        c.exchange(delivery(b, lease))
    current = snapshot(c, r)
    assert str(lease.endpoint.address) in current.suppressions[0]
    assert plan(current).counts["excluded"] == 1
    c.cancel(campaign)
    stale = change(r, at=datetime.now(UTC) - timedelta(milliseconds=500))
    with pytest.raises(ControlError, match="stopped"):
        submit(c, stale)
    assert scalar(pipeline, "SELECT count(*) FROM control_campaigns") == 1


def test_expired_plan_and_queued_expiration_no_authority(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    r = lab_request(lifetime_seconds=1)
    with pytest.raises(ControlError, match="schedule_expired"):
        submit(c, r)
    r = lab_request()
    campaign = submit(c, r)
    with transaction(pipeline.engine) as conn:
        conn.execute(
            text("UPDATE control_campaigns SET deadline=clock_timestamp()-interval '1 second'")
        )
    assert c.status() == {"cancelled": 2}
    assert report(c, campaign)["expired"] is True
    b = boot()
    register(c, b)
    assert c.exchange(Claim.model_validate(identity(b) | {"action": "claim"})).status == "idle"


def test_uncertainty_cannot_be_scheduled_again_and_snapshot_blocks_it(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    r = lab_request(queue_size=1)
    campaign = submit(c, r)
    b = boot()
    register(c, b)
    lease = claim(c, b)
    permit(c, b, lease)
    expire_lease(pipeline)
    assert c.status() == {"uncertain": 1}
    with pytest.raises(ControlError, match="unresolved_attempt"):
        submit(Coordinator(pipeline), change(r, at=datetime.now(UTC) - timedelta(milliseconds=500)))
    current = snapshot(c, r)
    assert current.blocked == (lease.endpoint,)
    assert plan(current).counts["blocked"] == 1
    assert report(c, campaign)["execution"]["incomplete_or_uncertain"] == 1  # type: ignore[index]
    # Original saved result can still deliver; this is not a new scheduled refresh.
    c.exchange(delivery(b, lease))
    assert report(c, campaign)["execution"]["measured"] == 1  # type: ignore[index]
    assert scalar(pipeline, "SELECT count(*) FROM control_attempts") == 1


@pytest.mark.parametrize("stage", ["schedule_before_commit", "schedule_after_commit"])
def test_scheduler_commit_failure_and_lost_ack_are_replay_safe(
    pipeline: Pipeline, stage: str
) -> None:
    r = lab_request()
    c = Coordinator(pipeline)

    def fail(actual: str) -> None:
        if actual == stage:
            raise RuntimeError("injected")

    pipeline.hook = fail
    with pytest.raises(RuntimeError):
        submit(c, r)
    assert scalar(pipeline, "SELECT count(*) FROM control_jobs") == (
        0 if stage.endswith("before_commit") else 2
    )
    pipeline.hook = lambda _: None
    campaign = submit(Coordinator(pipeline), r)
    assert submit(c, r) == campaign
    assert scalar(pipeline, "SELECT count(*) FROM control_jobs") == 2


def test_refresh_real_source_binding_negative_history_and_retained_counts(
    pipeline: Pipeline,
) -> None:
    c = Coordinator(pipeline)
    source = observation(age=3600, address="127.0.0.1", body=b"old evidence")
    source = Observation.model_validate(
        source.model_dump() | {"endpoint": {"address": "127.0.0.1", "port": 12345}}
    )
    pipeline.ingest(canonical(source), synthetic=True)
    r = lab_request(open_seconds=60)
    r = change(
        r, universe=r.universe.model_dump() | {"regions": [r.universe.regions[0]], "seeds": []}
    )
    with pytest.raises(ControlError, match="history_changed"):
        submit(c, r)
    current = snapshot(c, r)
    assert current.history == (summary(source),)
    campaign = submit(c, current)
    b = boot()
    register(c, b)
    lease = claim(c, b)
    assert lease.observation_id != source.observation_id
    assert permit(c, b, lease).status == "granted"
    sent = delivery(b, lease)
    c.exchange(sent)
    c.exchange(sent)
    assert pipeline.load(source.observation_id) == source
    assert scalar(pipeline, "SELECT last_evidence FROM current_services") == source.observation_id
    assert scalar(pipeline, "SELECT last_attempt FROM current_services") == lease.observation_id
    assert scalar(pipeline, "SELECT refresh_source_id FROM control_jobs") == source.observation_id
    counts = report(c, campaign)["execution"]
    assert isinstance(counts, dict) and counts["refreshed"] == counts["retained"] == 1
    assert plan(snapshot(c, r)).counts["fresh"] == 1  # Refusal cooldown, no older-open fallback.
    pipeline.maintain(suppress="127.0.0.1")
    counts = report(c, campaign)["execution"]
    assert isinstance(counts, dict) and counts["measured"] == 1 and counts["retained"] == 0


def test_refresh_rechecks_newer_source_and_actual_retention(pipeline: Pipeline) -> None:
    c = Coordinator(pipeline)
    r = lab_request(open_seconds=60)
    source = observation(age=3600, address="127.0.0.1")
    source = Observation.model_validate(
        source.model_dump() | {"endpoint": {"address": "127.0.0.1", "port": 12345}}
    )
    pipeline.ingest(canonical(source), synthetic=True)
    current = snapshot(c, r)
    newer = Observation.model_validate(
        source.model_dump()
        | {
            "observation_id": uuid4(),
            "started_at": datetime.now(UTC) - timedelta(seconds=5),
            "finished_at": datetime.now(UTC) - timedelta(seconds=4),
        }
    )
    pipeline.ingest(canonical(newer), synthetic=True)
    with pytest.raises(ControlError, match="history_changed"):
        submit(c, current)
    assert scalar(pipeline, "SELECT count(*) FROM control_jobs") == 0


def test_populated_0005_upgrade_preserves_fences_sources_and_schedule_restore_stop(
    empty_engine: Engine,
    tmp_path: Path,
) -> None:
    import subprocess

    from sqlalchemy import create_engine

    from netatlas.storage.backup import backup, compose_command, restore

    migrate(empty_engine, "0005")
    p = Pipeline(empty_engine, BlobStore(tmp_path / "blobs"))
    source = observation()
    p.ingest(canonical(source), synthetic=True)
    worker = uuid4()
    with transaction(empty_engine) as conn:
        conn.execute(
            text("INSERT INTO control_workers VALUES (:id,:session,12,clock_timestamp())"),
            {"id": worker, "session": uuid4()},
        )
        conn.execute(
            text("INSERT INTO control_pacing VALUES ('global',clock_timestamp(),clock_timestamp())")
        )
    migrate(empty_engine)
    assert scalar(p, "SELECT generation FROM control_workers") == 12
    assert p.load(source.observation_id) == source
    c = Coordinator(p)
    r = lab_request()
    campaign = submit(c, r)
    archive = tmp_path / "backups" / "schedule"
    backup(empty_engine, p.blobs, archive)
    name = "netatlas_restore_" + uuid4().hex
    subprocess.run(
        [*compose_command(), "createdb", "-U", "postgres", name], check=True, capture_output=True
    )
    engine = create_engine(empty_engine.url.set(database=name), hide_parameters=True)
    try:
        blobs = BlobStore(tmp_path / "restored")
        assert restore(engine, blobs, archive)["observations"] == 1
        recovered = Coordinator(Pipeline(engine, blobs))
        assert report(recovered, campaign)["global_stopped"] is True
        assert recovered.status() == {"cancelled": 2}
        assert submit(recovered, r) == campaign
        with pytest.raises(ControlError, match="stopped"):
            queue(recovered, 12346)
    finally:
        engine.dispose()
        subprocess.run(
            [*compose_command(), "dropdb", "-U", "postgres", "--force", name],
            check=True,
            capture_output=True,
        )


def test_storage_unavailable_and_global_queue_bound_leave_no_partial_admission(
    pipeline: Pipeline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.exc import OperationalError

    c, r = Coordinator(pipeline), lab_request()

    def unavailable(*args: Any) -> Any:
        raise OperationalError("unavailable", {}, Exception("fixture"))

    with monkeypatch.context() as patch:
        patch.setattr("netatlas.scheduler.service.transaction", unavailable)
        with pytest.raises(OperationalError):
            submit(c, r)
    assert scalar(pipeline, "SELECT count(*) FROM control_jobs") == 0
    with monkeypatch.context() as patch:
        patch.setattr("netatlas.control.coordinator.MAX_JOBS", 1)
        with pytest.raises(ControlError, match="queue_full"):
            submit(c, r)
    assert scalar(pipeline, "SELECT count(*) FROM control_campaigns") == 0
    campaign = submit(c, r)
    assert report(c, campaign)["execution"]["scheduled"] == 2  # type: ignore[index]


def test_partial_enqueue_expiration_rolls_back_and_report_uses_actual_retention(
    pipeline: Pipeline,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    c, r = Coordinator(pipeline), lab_request()
    times = iter((r.at + timedelta(seconds=1), r.expires_at))
    with monkeypatch.context() as patch:
        patch.setattr("netatlas.scheduler.service.clock", lambda _: next(times))
        with pytest.raises(ControlError, match="schedule_expired"):
            submit(c, r)
    assert scalar(pipeline, "SELECT count(*) FROM control_jobs") == 0
    campaign = submit(c, r)
    b = boot()
    register(c, b)
    lease = claim(c, b)
    permit(c, b, lease)
    c.exchange(delivery(b, lease))
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 1
    with monkeypatch.context() as patch:
        patch.setattr("netatlas.scheduler.service.clock", lambda _: r.at + timedelta(days=31))
        counts = report(c, campaign)["execution"]
        assert isinstance(counts, dict) and counts["retained"] == 0 and counts["measured"] == 1
    # No maintenance deletion was required for the retention decision.
    assert scalar(pipeline, "SELECT count(*) FROM observations") == 1


def test_plan_identity_changes_with_config_policy_seed_origin_and_history() -> None:
    r = request()
    baseline = plan(r)
    changed = (
        change(r, settings=config(global_connections_per_second=2)),
        change(r, policy={"seed": 1}),
        change(r, universe=r.universe.model_dump() | {"version": "2"}),
        change(
            r,
            universe=r.universe.model_dump()
            | {"origins": [r.universe.origins[0].model_dump() | {"content_sha256": "b" * 64}]},
        ),
        change(r, suppressions=["192.0.2.0/32"]),
    )
    for modified in changed:
        result = plan(modified)
        assert result.input_sha256 != baseline.input_sha256
        assert set(e.identity for e in result.entries).isdisjoint(
            e.identity for e in baseline.entries
        )
    assert plan(change(r, policy={"seed": 1})).seeds_sha256 == baseline.seeds_sha256
