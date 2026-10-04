"""Pure lookups: separate IPv4/IPv6 longest-prefix matching, no network or storage I/O."""

from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Literal

from netatlas.derivations.engine import canonical, digest
from netatlas.domain import ObservationV1
from netatlas.enrichment.models import Dataset, Enrichment, Place, Prefix
from netatlas.observation import Observation


def longest_prefix[T: Prefix](address: IPv4Address | IPv6Address, rows: tuple[T, ...]) -> T | None:
    # Bounded demonstration datasets: at most 4096 rows per dimension.
    matches = (row for row in rows if address in row.network)
    return max(matches, key=lambda row: row.network.prefixlen, default=None)


def places_named(dataset: Dataset, name: str, country: str | None = None) -> tuple[Place, ...]:
    """Exact casefolded name, retaining same-name alternatives by stable source ID."""
    return tuple(
        sorted(
            (
                p
                for p in dataset.places
                if p.name.casefold() == name.casefold()
                and (country is None or p.country_code == country)
            ),
            key=lambda p: p.id,
        )
    )


def enrich(source: ObservationV1 | Observation, dataset: Dataset, at: datetime) -> Enrichment:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("explicit aware evaluation clock required")
    at = at.astimezone(UTC)
    state: Literal["valid", "stale", "not_yet_valid"] = (
        "stale"
        if at >= dataset.expires_at
        else ("not_yet_valid" if at < dataset.valid_from else "valid")
    )
    network = (
        longest_prefix(source.endpoint.address, dataset.asn_prefixes) if state == "valid" else None
    )
    city = (
        longest_prefix(source.endpoint.address, dataset.city_prefixes) if state == "valid" else None
    )
    place = next((p for p in dataset.places if city and p.id == city.place_id), None)
    notes = []
    if state != "valid":
        notes.append("dataset_" + state)
    if network is None:
        notes.append("asn_unknown")
    elif len(network.asns) > 1:
        notes.append("multiple_origin_asns")
    if city is None:
        notes.append("city_unknown")
    elif city.accuracy_radius_km is None:
        notes.append("accuracy_radius_unknown")
    if place is not None and place.point is None:
        notes.append("coordinates_unknown")
    return Enrichment(
        source_observation_id=source.observation_id,
        source_schema_version=source.schema_version,
        source_sha256=digest(canonical(source)),
        dataset_id=dataset.id,
        dataset_version=dataset.version,
        dataset_sha256=digest(canonical(dataset)),
        evaluated_at=at,
        dataset_state=state,
        network=network,
        city=city,
        place=place,
        origins=dataset.origins,
        notes=tuple(sorted(notes)),
    )
