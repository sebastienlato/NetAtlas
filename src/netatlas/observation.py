"""Schema v2 and explicit version-dispatched readers (v1 is never silently upgraded)."""

from typing import Annotated, Literal, Self

from pydantic import Field, TypeAdapter, model_validator

from netatlas.domain import ObservationBase, ObservationV1, Outcome
from netatlas.evidence import ProtocolEvidence


class Observation(ObservationBase):
    schema_version: Literal[2] = 2
    protocol_evidence: ProtocolEvidence | None = None

    @model_validator(mode="after")
    def consistent_protocol_evidence(self) -> Self:
        if self.protocol_evidence:
            if self.response is not None:
                raise ValueError("v2 protocol captures belong only inside protocol_evidence")
            connected = any(e.tcp_outcome == Outcome.OPEN for e in self.protocol_evidence.exchanges)
            if connected != (self.outcome == Outcome.OPEN):
                raise ValueError("reachability must agree with protocol connections")
        return self


observation_reader: TypeAdapter[ObservationV1 | Observation] = TypeAdapter(
    Annotated[ObservationV1 | Observation, Field(discriminator="schema_version")]
)
