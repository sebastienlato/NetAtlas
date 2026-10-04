# Phase 5 — offline network and geographic enrichment

Package 0.6.0 adds dataset/result schema 1 and engine `enrichment-1`. Observation
v1/v2, config v3 and fingerprint contracts are unchanged. Enrichment reads the
endpoint address, not embedded legacy network/geography claims or banners. It
opens no sockets, follows no URLs, and never modifies original observations.
Only authored synthetic observations may enter durable storage.

## Dataset choice and licensing review (2026-10-04)

| Source | Reviewed terms and reuse | Decision |
| --- | --- | --- |
| [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/) and [110m places v5.1.2](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-populated-places/) | Raster/vector data is public domain; modification and redistribution, including commercial use, need no permission or mandatory credit. Optional credit: “Made with Natural Earth.” Data has accuracy/completeness limitations. | Selected Suva point and Fiji generalized country boundary from pinned v5.1.2 GeoJSON. Retain voluntary attribution and exact source hashes. No population attributes imported. |
| [DB-IP Lite](https://db-ip.com/db/lite.php), [FAQ](https://db-ip.com/faq.php) | ASN and city Lite downloads are monthly, reduced-coverage/accuracy subsets under CC BY 4.0. Redistribution/commercial use allowed subject to attribution. DB-IP requests a link to DB-IP.com on web pages using results. | Candidate for a separately reviewed bounded normalization adapter; not imported or bundled. No paid DB/API dependency. |
| [GeoNames export](https://www.geonames.org/export/) and [license notice](https://www.geonames.org/) | Downloadable data is CC BY 4.0, commercial use allowed, without accuracy/timeliness/completeness warranty; credit GeoNames with a link or reference. Offline downloads avoid the account/quota-dependent web service. | Candidate for a larger gazetteer; not imported or bundled. |

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) permits sharing and
adaptation with appropriate credit, license link, retained notices, indication of
changes and no additional legal/technical restrictions on licensed rights. A future
import/display must retain these obligations, including provider-specific attribution.
No third-party license grants a license to NetAtlas itself; the repository's
publication/license decision remains deferred. No commercial discovery database is used.

The demonstration intentionally combines **real public-domain place data with
fictional documentation-IP/ASN associations**. Natural Earth is not an IP location
or routing database. The fictional mappings demonstrate the offline pipeline, not
real coverage, ASN ownership or geolocation quality. The committed fixture contains
only authored synthetic data; all downloaded files and generated subsets stay in
ignored `data/`. No runtime fetcher or automatic dataset refresh is implemented.

## Dataset and result contracts

`enrichment/models.py` defines a bounded normalized bundle containing:

- ID/version, inclusive `valid_from` and exclusive `expires_at` in UTC; explicit
  operator-chosen validity window. For combined sources use the earliest applicable
  expiry; ingestion time does not refresh a dataset. The demo window is an authored
  October 2026 test window, not a claim Natural Earth was released then.
- Origins: source ID/version/URL, original-file SHA-256, license/link, attribution and
  modification notes. URLs are inert metadata. Operator review must establish rights
  and source provenance; validation/checksums do not authenticate those claims.
- Independent ASN-prefix and city-prefix rows, each with an origin reference.
  Canonical strict CIDRs reject host bits and duplicate equal prefixes. ASN tuples
  retain multiple origins, sorted without choosing an arbitrary owner. They are
  dataset assertions, not authorization, current routing or physical ownership.
- Places with stable source IDs, name, country/admin codes, kind, optional WGS84 point
  and optional MultiPolygon boundary. Names are not keys. `places_named` returns all
  exact casefolded name matches, optionally narrowed by country, sorted by ID.
- City-prefix rows link place IDs and optionally a positive provider-reported
  `accuracy_radius_km`. Missing radius stays null/unknown, never zero. The demo has
  no claimed radius. A centroid coordinate's decimals do not express accuracy.

Longest-prefix matching is independent for IPv4/IPv6 and ASN/city dimensions.
There is no cross-family or IPv4-mapped-IPv6 fallback. More-specific prefixes win;
unknown coverage does not trigger probing, DNS, nearest-city guesses, or fallback
from ASN organization names. Prefix lookup scans bounded rows; it is not a global
routing-table index. Multiple origin ASNs do not imply multiple devices.

Every result links source UUID/schema/canonical SHA-256, dataset ID/version/canonical
SHA-256, engine/schema version, explicit aware `evaluated_at`, dataset state,
matching prefix rows, place, all origin attributions and stable notes. The location
meaning is always `approximate_area_not_person_or_device`. Raw response bytes and
endpoint addresses are not copied into results. Place membership comes from the
explicit dataset ID association; no device location or boundary membership is inferred.

At evaluation before validity or at/after expiry, both dimensions return unknown,
with `not_yet_valid`/`stale` and diagnostic notes. Missing prefixes, coordinates and
radius remain explicit. The operator supplies `--at`; there is no hidden wall clock.
Same source/bundle/time/engine yields byte-identical output. Replay uses the recorded
clock, not today's freshness. **Future current searches must also test the dataset's
expiry against their query clock**; an old valid result is not perpetually fresh.

Canonical hashing uses validated defaults, sorted object keys, compact ASCII JSON
and ordered arrays, exactly the shared fingerprint serialization. File SHA-256
checks exact input bytes separately. Same-version edits have different canonical
identities; operators should still bump versions for semantic changes. Preserve
original download files when auditing upstream provenance; replay needs the retained
normalized bundle. Checksums establish equality, not source trust.

## Bounds, geometry and private files

Dataset files: 2 MiB; 16 origins; 4096 places, 4096 ASN rows and 4096 city rows;
512-character labels; 96-character IDs. Up to 16 ASN candidates per prefix. Boundaries
have at most 128 polygons, 32 rings/polygon, 4096 vertices/ring and 8192 total vertices.
JSON duplicate keys, nesting over 32, unknown schemas, dangling IDs, malformed ranges,
nonfinite/out-of-range coordinates and inconsistent radius claims fail closed.
Input datasets must be regular non-symlink files and match the required `--sha256`.

Coordinates are longitude/latitude, SRID 4326. Rings must close, have three distinct
vertices and be split at the antimeridian (no segment jumps more than 180 degrees).
`bounding_boundary` splits crossing boxes into east/west polygons and very wide boxes
into smaller parts. It labels no real administrative boundary; authored fixture
boundaries are explicitly synthetic. Natural Earth boundaries are generalized,
incomplete at 1:110m and not legal/survey boundaries. Holes and multiple polygons
are retained. Offline validation checks structure, bounds and splitting; **PostGIS
additionally checks full OGC topology**, rejecting self-intersection rather than
silently repairing it. Offline output alone is not a topology-validation certificate.

Storage points use `geography(Point,4326)` so [ST_DWithin](https://postgis.net/docs/ST_DWithin.html)
uses metres/spheroidal distance. Boundaries use `geometry(MultiPolygon,4326)` for
split planar coverage. [ST_IsValid](https://postgis.net/docs/ST_IsValid.html) runs
without content-bearing notices. Tests cover both sides of the dateline, exclusion
of Greenwich and metre thresholds. This phase does not add a geographic search API,
spatial index workload, map UI, geocoder, or coordinate transformation/network grids.

The offline apply command reuses bounded observation v1/v2 readers (16 MiB,
1024 rows, 1 MiB/row). Results are capped at 32 MiB, built privately then fsynced and
published atomically without overwrite under ignored `data/` as mode 0600. A bad later
row publishes no partial final file. Errors omit input contents. Offline outputs
have no automatic retention; remove them and downloads separately when required.

## Reproducible offline demonstration

Acquire these two freely usable fixed-release source files once. These downloads
are data acquisition from the publisher, not target measurements. Tests never fetch.
From the repository root:

```sh
umask 077
mkdir -p data/enrichment
curl --fail --location 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_110m_populated_places_simple.geojson' -o data/enrichment/places.geojson
curl --fail --location 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_110m_admin_0_countries.geojson' -o data/enrichment/countries.geojson
uv run --locked python -m netatlas.enrichment.demo --places data/enrichment/places.geojson --countries data/enrichment/countries.geojson --output data/enrichment/demo.json
```

The converter verifies these exact SHA-256 values before parsing:

| File | SHA-256 |
| --- | --- |
| Populated places simple | `0dbd25c9ad8bd797ddf164b067f563be5c16be2c002254eb594862377963f9dc` |
| Countries | `6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f` |
| Normalized demo bundle | `fd2ac4a1cbf0aab45fe64280233656c1951c0f7945542378de0927fb7895b29f` |

It selects by upstream NE_ID, retaining Suva (`ne:1159150917`) and Fiji
(`ne:1159320625`). It invents mappings from `192.0.2.0/24` and `2001:db8::/32` to
AS64496/Suva. Those associations are **not Natural Earth assertions** and have a
separate synthetic origin/checksum. No country polygon is used as a city accuracy area.

```sh
uv run --locked netatlas example | uv run --locked python -c 'import json,sys; print(json.dumps(json.load(sys.stdin)))' > data/enrichment/example.jsonl
uv run --locked netatlas-enrich --dataset data/enrichment/demo.json --sha256 fd2ac4a1cbf0aab45fe64280233656c1951c0f7945542378de0927fb7895b29f inspect
uv run --locked netatlas-enrich --dataset data/enrichment/demo.json --sha256 fd2ac4a1cbf0aab45fe64280233656c1951c0f7945542378de0927fb7895b29f apply --input data/enrichment/example.jsonl --output data/enrichment/example-derived.jsonl --at 2026-10-04T00:00:00Z
uv run --locked netatlas-enrich --dataset data/enrichment/demo.json --sha256 fd2ac4a1cbf0aab45fe64280233656c1951c0f7945542378de0927fb7895b29f places --name Suva --country FJ
```

Use new output names when repeating. The fixed synthetic example is suitable for
offline replay even after source retention would prevent DB ingestion. To demonstrate
durable storage, create a fresh synthetic observation using STORAGE's example,
ingest it, and use its UUID:

```sh
uv run --locked netatlas-store enrich --id OBSERVATION_UUID --dataset data/enrichment/demo.json --sha256 fd2ac4a1cbf0aab45fe64280233656c1951c0f7945542378de0927fb7895b29f --at 2026-10-04T00:00:00Z
uv run --locked netatlas-store verify
```

The verified local demo produced AS64496/Suva, unknown accuracy radius, the original
source hash, the two upstream file hashes and fictional mapping attribution. Suva
and the split Fiji polygon were persisted, then independently replayed. No real
observation, network measurement or real-world accuracy evaluation was performed.

## Storage, migration and removal

Migration **0003** creates PostGIS and three independent tables:
`enrichment_datasets` (canonical normalized snapshots), `places` (snapshot-linked
WGS84 gazetteer projections), and `enrichments` (immutable results plus source,
dataset, engine, evaluation time, optional place/point). UPDATE rejection protects
all three. Foreign keys bind results to observations and dataset-specific places.
No original source columns are rewritten. Basic FK indexes support maintenance;
search/facet/spatial workload indexes belong to Phase 6.

`store_enrichment` reconstructs a live unexpired source under the existing advisory
lock; dataset, places, result and a `derivation` outbox event commit together. Replay
is idempotent by source/dataset/engine/evaluation time with a full-result hash conflict
check. Different versions, hashes or evaluation clocks coexist. No uploaded derived
record is trusted, and unknown/stale results have null point/place projections.
The generic source-level outbox kind intentionally covers fingerprint and enrichment
changes. Future consumers must rebuild from live authoritative state.

`verify` now returns observation, fingerprint-derivation **and enrichment** counts.
It recomputes results and compares canonical snapshots, IDs, scalar projections,
points and boundaries. Expired source reads fail. Expiry/suppression cascades to
results; maintenance removes unreferenced snapshots and their gazetteer rows while
preserving snapshots still used by another source. Existing tombstone, outbox,
blob-GC and 7-day backup rules remain. Dataset files/offline results are independent
copies and require separate removal. No real ingestion or public raw display is enabled.

Backups include spatial extension declarations, snapshots, geography and results.
Restore into an empty PostGIS-capable server automatically applies newer migrations,
then expiry and replay verification. Integration tests cover populated Phase 4
archive restore to 0003 and Phase 5 spatial archive restore, plus lost acknowledgement,
transaction rollback, tampered projection detection and shared-snapshot removal.

## Phase 6 query consumer

The local search adapter now enforces the required dataset validity check at current
query time and actual source expiry in every mode. It selects one explicit dataset
hash and latest evaluation at/before as_of; unknown/stale mappings do not supply
coordinates/ASN filters. Radius/box/boundary areas test representative points and
retain provider radius metadata without claiming exact location. Migration 0004
adds spatial and structured indexes. See [SEARCH.md](SEARCH.md); HTTP routes/UI and
worldwide enrichment coverage remain unimplemented.
