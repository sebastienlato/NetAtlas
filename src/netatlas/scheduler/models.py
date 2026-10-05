"""Bounded authored-universe contracts. These models perform no I/O."""

from datetime import UTC, timedelta
from ipaddress import ip_address, ip_network
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator, model_validator

from netatlas.config import Settings
from netatlas.domain import Endpoint, Model, Outcome

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Label = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[ -~]+$")]
Port = Annotated[int, Field(strict=True, ge=1, le=65535)]
SYNTHETIC_NETWORKS = tuple(
    ip_network(n)
    for n in (
        "192.0.2.0/24",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "2001:db8::/32",
        "127.0.0.1/32",
        "::1/128",
    )
)


class Origin(Model):
    id: Label
    version: Label
    content_sha256: Hash
    attribution: Label
    license: Label
    kind: Literal["authored-synthetic"] = "authored-synthetic"


class Region(Model):
    network: str = Field(max_length=64)
    state: Literal["routed", "unrouted", "unknown"]
    origin_id: Label

    @field_validator("network")
    @classmethod
    def network_literal(cls, value: str) -> str:
        network = ip_network(value, strict=True)
        if "%" in value or not any(
            network.version == n.version
            and int(network.network_address) >= int(n.network_address)
            and int(network.broadcast_address) <= int(n.broadcast_address)
            for n in SYNTHETIC_NETWORKS
        ):
            raise ValueError("authored documentation or literal-loopback universe required")
        return str(network)


class Seed(Model):
    address: str = Field(max_length=64)
    origin_id: Label

    @field_validator("address")
    @classmethod
    def ipv6_literal(cls, value: str) -> str:
        address = ip_address(value)
        if address.version != 6 or "%" in value:
            raise ValueError("unscoped IPv6 seed required")
        return str(address)


class Universe(Model):
    schema_version: Literal[1] = 1
    id: Label
    version: Label
    valid_from: AwareDatetime
    expires_at: AwareDatetime
    origins: tuple[Origin, ...] = Field(min_length=1, max_length=16)
    regions: tuple[Region, ...] = Field(min_length=1, max_length=128)
    seeds: tuple[Seed, ...] = Field(default=(), max_length=1024)
    ports: tuple[Port, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def bounded_universe(self) -> Self:
        if self.valid_from >= self.expires_at:
            raise ValueError("ordered universe validity required")
        origins = {o.id for o in self.origins}
        if len(origins) != len(self.origins) or len(set(self.ports)) != len(self.ports):
            raise ValueError("duplicate origin or port")
        networks = [ip_network(r.network) for r in self.regions]
        if sum(n.num_addresses for n in networks if n.version == 4) > 4096:
            raise ValueError("IPv4 universe bound before enumeration")
        for index, network in enumerate(networks):
            if self.regions[index].origin_id not in origins or any(
                network.version == n.version and network.overlaps(n) for n in networks[:index]
            ):
                raise ValueError("overlapping regions or unknown origin")
        if len({s.address for s in self.seeds}) != len(self.seeds):
            raise ValueError("duplicate seed")
        for seed in self.seeds:
            if seed.origin_id not in origins or not any(
                ip_address(seed.address) in n for n in networks
            ):
                raise ValueError("seed requires declared region and origin")
        addresses = sum(n.num_addresses for n in networks if n.version == 4) + len(self.seeds)
        if addresses * len(self.ports) > 16384:
            raise ValueError("endpoint universe bound")
        return self


class Policy(Model):
    schema_version: Literal[1] = 1
    algorithm: Literal["coverage-refresh-1"] = "coverage-refresh-1"
    ipv6: Literal["explicit-authored-seeds-only-1"] = "explicit-authored-seeds-only-1"
    seed: int = Field(default=0, strict=True, ge=0, le=2**64 - 1)
    round: int = Field(default=0, strict=True, ge=0, le=2147483647)
    shards: int = Field(default=1, strict=True, ge=1, le=32)
    sample_per_prefix: int = Field(default=128, strict=True, ge=1, le=128)
    queue_size: int = Field(default=128, strict=True, ge=1, le=128)
    lifetime_seconds: int = Field(default=300, strict=True, ge=1, le=3600)
    open_seconds: int = Field(default=86400, strict=True, ge=60, le=2592000)
    closed_seconds: int = Field(default=604800, strict=True, ge=60, le=2592000)
    uncertain_seconds: int = Field(default=172800, strict=True, ge=60, le=2592000)


class Source(Model):
    endpoint: Endpoint
    observation_id: UUID
    source_sha256: Hash
    started_at: AwareDatetime
    finished_at: AwareDatetime
    outcome: Outcome

    @model_validator(mode="after")
    def time_order(self) -> Self:
        if self.started_at > self.finished_at or self.endpoint.transport.value != "tcp":
            raise ValueError("ordered TCP source required")
        return self


class PlanningInput(Model):
    schema_version: Literal[1] = 1
    lab_loopback: bool = False
    universe: Universe
    policy: Policy = Policy()
    settings: Settings = Settings()
    at: AwareDatetime
    history: tuple[Source, ...] = Field(default=(), max_length=4096)
    blocked: tuple[Endpoint, ...] = Field(default=(), max_length=1024)
    suppressions: tuple[str, ...] = Field(default=(), max_length=1024)

    @field_validator("suppressions")
    @classmethod
    def canonical_cidrs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any("%" in n for n in value):
            raise ValueError("unscoped prefixes required")
        return tuple(sorted({str(ip_network(n, strict=True)) for n in value}))

    @field_validator("at")
    @classmethod
    def utc_clock(cls, value: AwareDatetime) -> AwareDatetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def identities(self) -> Self:
        if len({s.observation_id for s in self.history}) != len(self.history):
            raise ValueError("duplicate source identity")
        if any(s.finished_at > self.at for s in self.history):
            raise ValueError("future source history")
        return self

    @property
    def expires_at(self) -> AwareDatetime:
        return min(
            self.universe.expires_at, self.at + timedelta(seconds=self.policy.lifetime_seconds)
        )


class Entry(Model):
    identity: Hash
    endpoint: Endpoint
    prefix: str
    region: str
    origin_id: str
    seed_origin_id: str | None = None
    shard: int
    kind: Literal["coverage", "refresh"]
    due_at: AwareDatetime
    previous: Source | None = None


class Plan(Model):
    schema_version: Literal[1] = 1
    input_sha256: Hash
    universe_sha256: Hash
    policy_sha256: Hash
    seeds_sha256: Hash
    config_sha256: Hash
    connection_policy_sha256: Hash
    at: AwareDatetime
    expires_at: AwareDatetime
    counts: dict[str, int]
    entries: tuple[Entry, ...] = Field(max_length=128)
