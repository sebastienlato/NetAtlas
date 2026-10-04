"""Bound scope before expansion; stream reproducibly without an endpoint list."""

import random
from collections import Counter
from collections.abc import Iterator
from ipaddress import IPv4Network, IPv6Network, collapse_addresses, ip_network
from typing import Annotated, Self

from pydantic import Field, model_validator

from netatlas.config import MeasurementSettings
from netatlas.discovery.policy import Address, denial
from netatlas.domain import Endpoint, Model


class Scope(Model):
    targets: tuple[str, ...] = Field(min_length=1, max_length=256)
    ports: tuple[Annotated[int, Field(strict=True, ge=1, le=65535)], ...] = Field(
        min_length=1, max_length=64
    )
    seed: int = Field(default=0, ge=0, le=2**64 - 1, strict=True)
    lab_loopback: bool = False

    @model_validator(mode="after")
    def literals_and_ports(self) -> Self:
        for target in self.targets:
            if len(target) > 64 or "%" in target:
                raise ValueError("targets must be unscoped literal addresses or strict CIDRs")
            ip_network(target, strict=True)
            if self.lab_loopback and target not in {"127.0.0.1", "::1"}:
                raise ValueError("lab mode accepts only literal 127.0.0.1 and ::1")
        if any(type(port) is not int or not 1 <= port <= 65535 for port in self.ports):
            raise ValueError("ports must be integers in 1..65535")
        if self.lab_loopback and len(self.ports) > 16:
            raise ValueError("lab mode permits at most 16 ports")
        return self

    def networks(self, settings: MeasurementSettings) -> tuple[IPv4Network | IPv6Network, ...]:
        parsed = tuple(ip_network(target) for target in self.targets)
        # Integer arithmetic before ANY expansion, including denied/overlapping ranges.
        addresses = sum(network.num_addresses for network in parsed)
        if (
            addresses > settings.max_addresses
            or addresses * len(self.ports) > settings.max_endpoints
        ):
            raise ValueError("requested scope exceeds address or endpoint budget")
        v4 = [network for network in parsed if isinstance(network, IPv4Network)]
        v6 = [network for network in parsed if isinstance(network, IPv6Network)]
        networks: list[IPv4Network | IPv6Network] = [
            *collapse_addresses(v4),
            *collapse_addresses(v6),
        ]
        random.Random(self.seed).shuffle(networks)
        return tuple(networks)

    def addresses(self, settings: MeasurementSettings) -> Iterator[Address]:
        rng = random.Random(self.seed)
        for network in self.networks(settings):
            offset = rng.randrange(network.num_addresses)
            for index in range(network.num_addresses):
                yield network[(offset + index) % network.num_addresses]

    def endpoints(self, settings: MeasurementSettings) -> Iterator[Endpoint]:
        ports = sorted(set(self.ports))
        random.Random(self.seed).shuffle(ports)
        for address in self.addresses(settings):
            if denial(address, settings, lab=self.lab_loopback) is None:
                for port in ports:
                    yield Endpoint(address=address, port=port)

    def preview(self, settings: MeasurementSettings) -> dict[str, object]:
        counts: Counter[str] = Counter()
        for address in self.addresses(settings):
            counts[denial(address, settings, lab=self.lab_loopback) or "eligible"] += 1
        return {
            "scope": self.model_dump(mode="json"),
            "addresses": sum(counts.values()),
            "address_decisions": dict(sorted(counts.items())),
            "eligible_endpoints": counts["eligible"] * len(set(self.ports)),
            "interaction_plan": {
                "strategy": "greeting-http-tls-v1"
                if settings.protocol_evidence
                else "connect-only-v1",
                "max_connections_per_endpoint": settings.max_connections_per_endpoint
                if settings.protocol_evidence
                else 1,
                "max_campaign_connections": counts["eligible"]
                * len(set(self.ports))
                * (settings.max_connections_per_endpoint if settings.protocol_evidence else 1),
                "max_received_bytes_per_endpoint": settings.max_response_bytes
                if settings.protocol_evidence
                else 0,
                "max_sent_bytes_per_endpoint": settings.max_sent_bytes
                if settings.protocol_evidence
                else 0,
                "max_retained_bytes_per_endpoint": settings.max_response_bytes
                if settings.protocol_evidence
                else 0,
                "steps": [
                    "listen for SSH/SMTP/unknown greeting",
                    "if silent, GET / with literal IP Host",
                    "if HTTP attempt unidentified, fresh TLS then greeting/GET; no retry",
                ][: 3 if settings.max_connections_per_endpoint == 2 else 2]
                if settings.protocol_evidence
                else ["TCP connect and close"],
                "dns": False,
                "retries": 0,
            },
            "order": "seeded-network-port-shuffle-and-address-rotation-v1",
        }
