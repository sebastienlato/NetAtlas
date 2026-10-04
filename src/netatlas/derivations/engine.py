"""Pure matching on bounded raw evidence; no ports, clocks, I/O or metadata trust."""

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from netatlas.derivations.models import (
    Candidate,
    Condition,
    Derivation,
    EvidenceReference,
    RulePack,
    Selector,
)
from netatlas.domain import CapturedResponse, Model, ObservationV1
from netatlas.observation import Observation
from netatlas.protocol_syntax import inspect

BODY_WINDOW = 8192
Note = Literal[
    "legacy_v1",
    "missing_evidence",
    "unrecognized_evidence",
    "malformed_evidence",
    "truncated_evidence",
    "encoded_body_skipped",
    "body_window_limited",
    "no_rule_match",
    "multiple_products",
    "multiple_categories",
]


def canonical(model: Model) -> bytes:
    return json.dumps(
        model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class FieldEvidence:
    selector: Selector
    start: int
    value: bytes
    complete: bool = True


def fields(data: bytes, notes: set[Note], *, truncated: bool) -> list[FieldEvidence]:
    """Reparse raw syntax instead of trusting possibly forged typed metadata."""
    parsed = inspect(data, eof=True)
    if parsed.status == "malformed":
        notes.add("malformed_evidence")
        return []
    result: list[FieldEvidence] = []
    if parsed.http:
        if not parsed.http.headers_complete or parsed.http.body_offset is None:
            notes.add("truncated_evidence")
            return []
        position = data.index(b"\r\n") + 2
        while position < parsed.http.body_offset - 2:
            end = data.index(b"\r\n", position)
            name, _, value = data[position:end].partition(b":")
            if name.lower() == b"server":
                start = position + len(name) + 1 + len(value) - len(value.lstrip(b" \t"))
                result.append(FieldEvidence("http.server", start, value.strip(b" \t")))
            position = end + 2
        if any(
            n.lower() in ("content-encoding", "transfer-encoding") for n, _ in parsed.http.headers
        ):
            notes.add("encoded_body_skipped")
        elif parsed.http.status >= 200 and parsed.http.status not in (204, 304):
            start = parsed.http.body_offset
            lengths = [int(v) for n, v in parsed.http.headers if n.lower() == "content-length"]
            size = min(len(data) - start, lengths[0]) if lengths else len(data) - start
            if size > BODY_WINDOW:
                notes.add("body_window_limited")
            if lengths and len(data) - start < lengths[0]:
                notes.add("truncated_evidence")
            result.append(
                FieldEvidence(
                    "http.body",
                    start,
                    data[start : start + min(size, BODY_WINDOW)],
                    complete=not truncated
                    and size <= BODY_WINDOW
                    and (not lengths or len(data) - start >= lengths[0]),
                )
            )
    elif parsed.ssh:
        position = 0
        for line in data.splitlines(keepends=True):
            if line.startswith(b"SSH-"):
                start = position + len(f"SSH-{parsed.ssh.protocol_version}-")
                result.append(
                    FieldEvidence("ssh.software", start, parsed.ssh.software.encode("ascii"))
                )
                break
            position += len(line)
    elif parsed.smtp:
        position = 0
        for greeting in parsed.smtp.greeting:
            hostname, separator, text = greeting.partition(" ")
            if separator:
                result.append(
                    FieldEvidence(
                        "smtp.greeting", position + 5 + len(hostname), text.encode("ascii")
                    )
                )
            position += len(greeting) + 6
    else:
        notes.add("unrecognized_evidence")
    return result


def match(condition: Condition, field: FieldEvidence) -> tuple[int, int] | None:
    if field.selector != condition.selector:
        return None
    needle = condition.value.encode("ascii")
    data = field.value
    index = -1
    match condition.operator:
        case "equals":
            if field.complete and data == needle:
                index = 0
        case "prefix":
            if data.startswith(needle):
                index = 0
        case "contains":
            index = data.find(needle)
        case "word":
            # Explicit ASCII word boundary, no user-supplied regular expressions.
            offset = 0
            while (found := data.find(needle, offset)) != -1:
                word = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                if (found == 0 or data[found - 1] not in word) and (
                    (found + len(needle) == len(data) and field.complete)
                    or (found + len(needle) < len(data) and data[found + len(needle)] not in word)
                ):
                    index = found
                    break
                offset = found + 1
    if index < 0:
        return None
    return field.start + index, field.start + index + len(needle)


def derive(observation: ObservationV1 | Observation, pack: RulePack) -> Derivation:
    notes: set[Note] = set()
    captures: list[tuple[str, CapturedResponse]] = []
    if isinstance(observation, ObservationV1):
        notes.add("legacy_v1")
    if isinstance(observation, Observation) and observation.protocol_evidence:
        captures.extend(
            (f"/protocol_evidence/exchanges/{index}/response/body_base64", exchange.response)
            for index, exchange in enumerate(observation.protocol_evidence.exchanges)
            if exchange.response is not None
        )
    elif observation.response:
        captures.append(("/response/body_base64", observation.response))
    if not captures:
        notes.add("missing_evidence")
    candidates: list[Candidate] = []
    for pointer, capture in captures:
        if capture.truncated:
            notes.add("truncated_evidence")
        data = base64.b64decode(capture.body_base64)
        available = fields(data, notes, truncated=capture.truncated)
        for rule in sorted(pack.rules, key=lambda r: r.rule_id):
            references: list[EvidenceReference] = []
            for index, condition in enumerate(rule.conditions):
                for field in available:
                    span = match(condition, field)
                    if span:
                        start, end = span
                        references.append(
                            EvidenceReference(
                                pointer=pointer,
                                selector=condition.selector,
                                condition_index=index,
                                start=start,
                                end=end,
                                sha256=digest(data[start:end]),
                            )
                        )
                        break
                else:
                    break
            if len(references) == len(rule.conditions):
                candidates.append(
                    Candidate(
                        rule_id=rule.rule_id,
                        rule_version=rule.version,
                        product=rule.product,
                        category=rule.category,
                        confidence=rule.confidence,
                        evidence=tuple(references),
                    )
                )
    products = {c.product for c in candidates if c.product is not None}
    categories = {c.category for c in candidates if c.category is not None}
    if not candidates:
        notes.add("no_rule_match")
    if len(products) > 1:
        notes.add("multiple_products")
    if len(categories) > 1:
        notes.add("multiple_categories")
    return Derivation(
        source_observation_id=observation.observation_id,
        source_schema_version=observation.schema_version,
        source_sha256=digest(canonical(observation)),
        pack_id=pack.pack_id,
        pack_version=pack.version,
        pack_sha256=digest(canonical(pack)),
        candidates=tuple(candidates),
        notes=tuple(sorted(notes)),
        product_state="unknown" if not products else "single" if len(products) == 1 else "multiple",
        category_state="unknown"
        if not categories
        else "single"
        if len(categories) == 1
        else "multiple",
    )
