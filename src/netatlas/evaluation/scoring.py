"""Multilabel counts with abstentions, unlabelled cases and undefined ratios explicit."""

import math
from datetime import datetime
from typing import Any

from netatlas.derivations.engine import canonical, derive, digest
from netatlas.derivations.offline import load_pack
from netatlas.domain import Category
from netatlas.evaluation.corpus import Corpus, source


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def wilson(successes: int, total: int) -> list[float] | None:
    """Nominal 95% binomial interval; not population inference for authored cases."""
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    scale = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / scale
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / scale
    return [max(0, centre - radius), min(1, centre + radius)]


def score(
    truth: list[set[str] | None], predictions: list[set[str]], labels: set[str]
) -> dict[str, Any]:
    if len(truth) != len(predictions):
        raise ValueError("paired evaluation rows required")
    scored = [(t, p) for t, p in zip(truth, predictions, strict=True) if t is not None]
    all_labels = labels | {x for t, p in scored for x in t | p}
    classes = {}
    for label in sorted(all_labels):
        tp = sum(label in t and label in p for t, p in scored)
        fp = sum(label not in t and label in p for t, p in scored)
        fn = sum(label in t and label not in p for t, p in scored)
        classes[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": tp + fn,
            "predicted": tp + fp,
            "precision": ratio(tp, tp + fp),
            "recall": ratio(tp, tp + fn),
            "precision_nominal_wilson95": wilson(tp, tp + fp),
            "recall_nominal_wilson95": wilson(tp, tp + fn),
        }
    return {
        "total_sources": len(truth),
        "labelled_sources": len(scored),
        "excluded_unlabelled_sources": len(truth) - len(scored),
        "predictions_on_unlabelled_sources": sum(
            len(p) for t, p in zip(truth, predictions, strict=True) if t is None
        ),
        "unknown_output_sources": sum(not p for p in predictions),
        "multiple_output_sources": sum(len(p) > 1 for p in predictions),
        "classes": classes,
    }


def evaluate(corpus: Corpus, at: datetime) -> dict[str, Any]:
    pack = load_pack()
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(corpus.cases, 1):
        observation = source(case, index, at)
        result = derive(observation, pack)
        products = sorted({c.product for c in result.candidates if c.product})
        roles = sorted({c.category.value for c in result.candidates if c.category})
        rows.append(
            {
                "case": case.id,
                "stratum": case.stratum,
                "products": products,
                "roles": roles,
                "candidate_records": len(result.candidates),
                "source_sha256": digest(canonical(observation)),
                "result_sha256": digest(canonical(result)),
                "notes": list(result.notes),
                "assertion_mismatch": case.products is not None
                and set(products) != set(case.products),
                "role_mismatch": case.roles is not None and set(roles) != set(case.roles),
                "identity_mismatch_if_misinterpreted": case.underlying_products is not None
                and set(products) != set(case.underlying_products),
            }
        )
    products_pred = [set(r["products"]) for r in rows]
    roles_pred = [set(r["roles"]) for r in rows]
    return {
        "corpus_sha256": digest(canonical(corpus)),
        "pack_sha256": digest(canonical(pack)),
        "engine": "fingerprints-1",
        "taxonomy": pack.taxonomy_version,
        "rows": rows,
        "product_assertions": score(
            [set(c.products) if c.products is not None else None for c in corpus.cases],
            products_pred,
            {"nginx", "OpenSSH", "Postfix", "Apache"},
        ),
        "category_scenarios": score(
            [set(c.roles) if c.roles is not None else None for c in corpus.cases],
            roles_pred,
            {c.value for c in Category if c != Category.UNKNOWN},
        ),
        "identity_counterexample_only": score(
            [
                set(c.underlying_products) if c.underlying_products is not None else None
                for c in corpus.cases
            ],
            products_pred,
            set(),
        ),
        "strata": {
            name: {
                "sources": len(selected := [r for r in rows if r["stratum"] == name]),
                "assertion_mismatches": sum(r["assertion_mismatch"] for r in selected),
                "role_mismatches": sum(r["role_mismatch"] for r in selected),
                "unknown_products": sum(not r["products"] for r in selected),
                "unknown_categories": sum(not r["roles"] for r in selected),
            }
            for name in sorted({c.stratum for c in corpus.cases})
        },
    }
