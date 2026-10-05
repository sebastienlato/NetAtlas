"""Authored labels are inputs, never obtained from fingerprint predictions."""

import base64
from datetime import datetime, timedelta
from importlib.resources import files
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from netatlas.config import Settings
from netatlas.domain import Category, Model, Outcome
from netatlas.examples import example_observation
from netatlas.observation import Observation


class Case(Model):
    id: str
    stratum: str
    captures: tuple[str, ...] = Field(max_length=2)
    products: tuple[str, ...] | None
    roles: tuple[Category, ...] | None
    underlying_products: tuple[str, ...] | None
    rationale: str
    truncated: bool = False
    outcome: Outcome = Outcome.OPEN


class Corpus(Model):
    schema_version: Literal[1]
    version: str
    method: str
    cases: tuple[Case, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("duplicate evaluation case")
        return self


def load_corpus() -> Corpus:
    return Corpus.model_validate_json(files(__package__).joinpath("corpus.json").read_bytes())


def source(case: Case, index: int, at: datetime, *, address: str = "192.0.2.10") -> Observation:
    row = example_observation(Settings()).model_dump(mode="json")
    row.update(
        observation_id=str(UUID(int=index)),
        started_at=at - timedelta(seconds=1),
        finished_at=at,
        service=None,
        response=None,
        network=None,
        geolocation=None,
        outcome=case.outcome,
    )
    row["target"].update(address=address, source="authored-evaluation-1")
    row["endpoint"].update(address=address, port=49152)
    if case.captures:
        captures = [raw.encode("utf-8") for raw in case.captures]
        row["protocol_evidence"] = {
            "exchanges": [
                {
                    "connection": i + 1,
                    "probe": "greeting-http" if i == 0 else "tls",
                    "tcp_outcome": "open",
                    "status": "unknown",
                    "response": {
                        "body_base64": base64.b64encode(raw).decode(),
                        "truncated": case.truncated,
                    },
                }
                for i, raw in enumerate(captures)
            ],
            "received_bytes": sum(map(len, captures)),
            "retained_bytes": sum(map(len, captures)),
            "sent_bytes": 0,
            "termination": "finished",
        }
    return Observation.model_validate(row)
