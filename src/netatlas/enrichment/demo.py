"""Build a tiny offline demo from explicitly acquired, checksum-pinned Natural Earth files.

The IP/ASN associations are authored fiction. No IP geolocation truth is claimed.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from netatlas.derivations.engine import canonical, digest
from netatlas.derivations.offline import regular_file, unique_object
from netatlas.enrichment.models import AsnPrefix, Boundary, CityPrefix, Dataset, Origin, Place
from netatlas.enrichment.offline import DATASET_BYTES, publish

BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/"
FILES = {
    "places": (
        "ne_110m_populated_places_simple.geojson",
        "0dbd25c9ad8bd797ddf164b067f563be5c16be2c002254eb594862377963f9dc",
    ),
    "countries": (
        "ne_110m_admin_0_countries.geojson",
        "6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f",
    ),
}


def features(path: Path, key: str) -> list[dict[str, Any]]:
    with regular_file(path) as stream:
        raw = stream.read(DATASET_BYTES + 1)
    if len(raw) > DATASET_BYTES or digest(raw) != FILES[key][1]:
        raise ValueError("Natural Earth input checksum failure")
    parsed = json.loads(raw, object_pairs_hook=unique_object)
    result: list[dict[str, Any]] = parsed["features"]
    return result


def build_demo(places: Path, countries: Path) -> Dataset:
    city = next(f for f in features(places, "places") if f["properties"]["ne_id"] == 1159150917)
    country = next(
        f for f in features(countries, "countries") if f["properties"]["NE_ID"] == 1159320625
    )
    origins = []
    for key, (filename, sha) in FILES.items():
        origins.append(
            Origin(
                id="natural-earth-" + key,
                version="5.1.2",
                source_url=BASE + filename,
                source_sha256=sha,
                license="Public domain",
                license_url="https://www.naturalearthdata.com/about/terms-of-use/",
                attribution="Made with Natural Earth. Contributors: Natural Earth / NACIS.",
                modifications=(
                    "Selected Suva point / Fiji generalized boundary; "
                    "omitted other features and attributes."
                ),
            )
        )
    mappings = (
        AsnPrefix(prefix="192.0.2.0/24", origin="synthetic", asns=(64496,)),
        AsnPrefix(prefix="2001:db8::/32", origin="synthetic", asns=(64496,)),
    )
    cities = tuple(
        CityPrefix(prefix=r.prefix, origin="synthetic", place_id="ne:1159150917") for r in mappings
    )
    origins.append(
        Origin(
            id="synthetic",
            version="1.0.0",
            source_url="urn:netatlas:fictional-demo-mappings",
            source_sha256=digest(b"\n".join(canonical(r) for r in (*mappings, *cities))),
            license="Authored demonstration; repository terms",
            license_url="urn:netatlas:repository-terms",
            attribution=(
                "NetAtlas fictional documentation-address/ASN mappings, "
                "not measured or geographic truth."
            ),
            modifications=(
                "Invented mappings to Suva solely for offline testing. "
                "Hash covers canonical mapping rows joined with newline."
            ),
        )
    )
    props = city["properties"]
    return Dataset(
        id="natural-earth-synthetic-demo",
        version="1.0.0",
        valid_from=datetime(2026, 10, 1, tzinfo=UTC),
        expires_at=datetime(2026, 11, 1, tzinfo=UTC),
        origins=tuple(origins),
        asn_prefixes=mappings,
        city_prefixes=cities,
        places=(
            Place(
                id="ne:1159150917",
                origin="natural-earth-places",
                name=props["name"],
                country_code=props["iso_a2"],
                admin_code=None,
                point=tuple(city["geometry"]["coordinates"]),
            ),
            Place(
                id="ne:1159320625",
                origin="natural-earth-countries",
                name="Fiji",
                country_code="FJ",
                kind="country",
                boundary=Boundary.model_validate(country["geometry"]),
                boundary_kind="generalized",
            ),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--places", type=Path, required=True)
    parser.add_argument("--countries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = canonical(build_demo(args.places, args.countries))
        publish(args.output, data)
        print(
            json.dumps(
                {
                    "sha256": digest(data),
                    "synthetic_ip_mappings": True,
                    "attribution": "Made with Natural Earth (public domain), v5.1.2.",
                }
            )
        )
    except ValueError, OSError, KeyError, TypeError, StopIteration:
        parser.exit(2, "Demo preparation failed; check pinned local files and new output.\n")


if __name__ == "__main__":
    main()
