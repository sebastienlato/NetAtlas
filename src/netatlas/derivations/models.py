"""Bounded declarative rules and independently versioned derived contracts."""

from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from netatlas.domain import Category, Model

Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9.-]*$")]
Version = Annotated[str, Field(max_length=32, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
Text = Annotated[str, Field(min_length=1, max_length=512, pattern=r"^[\x20-\x7e]+$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Selector = Literal["http.server", "http.body", "ssh.software", "smtp.greeting"]
Confidence = Literal["asserted", "corroborated"]


class Condition(Model):
    selector: Selector
    operator: Literal["equals", "prefix", "contains", "word"]
    value: Text


class Rule(Model):
    rule_id: Identifier
    version: Version
    description: Text
    provenance: Text
    product: Text | None = None
    category: Category | None = None
    confidence: Confidence = "asserted"
    conditions: tuple[Condition, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def meaningful_rule(self) -> Self:
        if self.product is None and self.category is None:
            raise ValueError("a rule needs a product or category")
        if self.category == Category.UNKNOWN:
            raise ValueError("unknown is a result, not a positive rule")
        protocols = {c.selector.split(".")[0] for c in self.conditions}
        if len(protocols) != 1:
            raise ValueError("conditions must refer to the same application protocol")
        if self.confidence == "corroborated" and len({c.selector for c in self.conditions}) < 2:
            raise ValueError("corroboration requires two distinct evidence fields")
        return self


class RulePack(Model):
    schema_version: Literal[1] = 1
    pack_id: Identifier
    version: Version
    taxonomy_version: Literal["netatlas-categories-1"] = "netatlas-categories-1"
    provenance: Text
    rules: tuple[Rule, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_rules(self) -> Self:
        if len({r.rule_id for r in self.rules}) != len(self.rules):
            raise ValueError("rule identifiers must be unique within a pack")
        return self


class EvidenceReference(Model):
    # JSON pointer identifies the base64 field; offsets index its decoded bytes.
    pointer: Annotated[
        str,
        Field(pattern=r"^/(response|protocol_evidence/exchanges/[01]/response)/body_base64$"),
    ]
    selector: Selector
    condition_index: int = Field(ge=0, le=3, strict=True)
    start: int = Field(ge=0, le=65535, strict=True)
    end: int = Field(ge=1, le=65536, strict=True)
    sha256: Digest

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("evidence range must be nonempty")
        return self


class Candidate(Model):
    rule_id: Identifier
    rule_version: Version
    product: Text | None
    category: Category | None
    confidence: Confidence
    evidence: tuple[EvidenceReference, ...] = Field(min_length=1, max_length=4)


class Derivation(Model):
    schema_version: Literal[1] = 1
    engine_version: Literal["fingerprints-1"] = "fingerprints-1"
    taxonomy_version: Literal["netatlas-categories-1"] = "netatlas-categories-1"
    source_observation_id: UUID
    source_schema_version: Literal[1, 2]
    source_sha256: Digest
    pack_id: Identifier
    pack_version: Version
    pack_sha256: Digest
    candidates: tuple[Candidate, ...] = Field(max_length=128)
    product_state: Literal["unknown", "single", "multiple"]
    category_state: Literal["unknown", "single", "multiple"]
    notes: tuple[
        Literal[
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
        ],
        ...,
    ] = Field(max_length=11)
