# Phase 6 — local search and aggregate statistics

Package 0.7.0 adds `netatlas.search`, query schema 1 and migration 0004. This is a
private local Python/CLI interface over synthetic PostgreSQL data. Phase 7 now adds a separate local HTTP adapter (see the final section); no
public service, geographic UI, external index or real inputs exist.
Collectors and domain/derivation engines do not import search. No query opens target
connections, resolves names, reads raw blobs or initiates measurement.

## Run locally

Use STORAGE's existing private database, then `make db-migrate`. Supply a regular
JSON file (maximum 16 KiB, duplicate keys/extra fields rejected, schema_version
required in files):

```sh
umask 077
mkdir -p data/search
cat > data/search/query.json <<'JSON'
{"schema_version":1,"mode":"current","selection":"evidence","network":"192.0.2.0/24","text":"nginx","limit":20}
JSON
uv run --locked netatlas-search --query data/search/query.json --output data/search/result.json
```

The console reports only endpoint, observation and candidate counts. Results go to
a new mode-0600 file under ignored `data/`, fsynced and atomically published without
overwrite. Use a fresh output name each time. The 4 MiB output limit fails without
publishing; reduce the page size for unusually large product-label sets. Parent
directories are operator managed; private file permissions are not protection from
a hostile local administrator. Output copies require independent removal like offline
derivations. Errors omit query values, SQL, connection details and labels.

Python callers use `search(engine, Query(...))`; the returned dictionary contains
`selection` (including resolved pack hash and as_of), `retention_checked_at`, exact
counts, bounded `hits`, bounded `facets`, and selected pack/dataset metadata including
versions, validity, origins, attribution and licensing (without full rules or prefix/place
collections). This local interface is not the eventual
HTTP wire contract. Phase 7 defines its separate allowlisted models and local access
policy in API.md; these private dictionaries remain separate. SQLAlchemy hides parameters; no query logging is added.

## Selection, clocks and version identity

An endpoint is canonical address + transport + port, never one physical device.
`mode=current` selects exactly one retained source per endpoint; `mode=history`
selects all eligible retained sources. `selection` chooses attempts (default, every
outcome), TCP-open observations, or observations with nonempty evidence. Current
selection orders by `(finished_at, started_at, UUID)` descending, independently of
arrival. UUID breaks ties deterministically; it is not additional physical chronology.

**Select the source before applying content, outcome, freshness or observation-window
filters.** A current timeout does not fall back to an older nginx source to satisfy a
text query. Request `selection=evidence` explicitly to search preserved older evidence.
An empty open attempt may be current for `open` while the older evidence remains
current for `evidence`. These are distinct views; a result does not imply uptime.
All modes return source timestamps and freshness, never silently combine one source's
category with another's network or geography.

`as_of` defaults to the UTC query clock captured after acquiring the pipeline lock.
Future clocks fail. Eligible observations finished at/before as_of; `after` is
inclusive and `before` exclusive on finish time. The default freshness threshold is
86400 seconds; `fresh_seconds` is 1–2592000. `freshness=any|fresh|stale` compares the
selected source with as_of minus that threshold (equality is fresh).

Retention always checks **actual query time**, including historical requests. An old
as_of cannot resurrect expired/deleted/suppressed data. Historical queries describe
currently retained observations through a chosen measurement clock, not an archive
of what the database/operator knew then. Deletion, later derivation and expiry can
change a repeat query. Offset pagination has no cross-request snapshot guarantee.

`pack_sha256=null` resolves to the bundled core pack's canonical hash. Specify an
exact canonical hash to select a different snapshot, including same-version edits.
Only `fingerprints-1` / `netatlas-categories-1` are supported. No result for that
identity means unknown, even when another pack produced candidates. No automatic
"latest version" fallback or combined-pack candidate ranking exists. Results retain
source hash and chosen derivation ID for private replay; confidence remains ordinal.

`dataset_sha256=null` deliberately disables enrichment. ASN/place/geo filters require
an explicit canonical dataset hash (distinct from a file checksum). For each source,
choose the latest evaluation at/before as_of for that hash and `enrichment-1`, ordered
by evaluated_at then ID. Do not select an older result merely because it matches a
filter. Selected result validity **and** dataset valid_from/expiry at as_of govern
whether mappings are usable. A formerly valid result becomes stale at dataset expiry
for current queries; historical as_of can inspect its earlier validity while the
source is still retained. Newly evaluated stale results remain unknown. Missing
results/hash coverage remain unknown; hashes and versions are not publisher trust.

## Filters and geography

All supplied filters are ANDed. Supported fields are literal address/CIDR (strict
network bits, IPv4/IPv6 kept separate), port, transport, outcome, has_evidence,
category, product text, observation window/freshness, ASN, country, stable place ID,
geography state, and one radius/box/place-boundary area. Unknown fields fail closed.

Text uses PostgreSQL `simple` full-text tokenization and `plainto_tsquery`: all input
terms must occur in product candidate labels across the selected derivation. It is
case-insensitive token search, not substring, fuzzy, phrase, regex or Boolean query
syntax. Maximum 256 printable characters. It indexes no banner, header, body,
certificate, URL or arbitrary peer metadata. Product names can still be untrusted
assertions; search output is private metadata, not a field-level sanitizer.

Categories are the existing taxonomy, including an explicit `unknown` filter.
Ambiguous candidates all remain supported; no winning category or device identity is
invented. A product-text match and category match may be supported by different
candidates of the same source. Candidate count is the complete selected derivation's
count, not the number of rules matching the query. Hit label arrays preserve candidate
multiplicity; facet values are deduplicated per source/endpoint.

`geography` is any, known (usable point), unknown (no usable point), stale or
not_yet_valid (selected dataset at as_of). A known place can lack a point; it still
matches its stable ID/country while geography is unknown. Same-name places never
collapse: use the offline gazetteer's exact-name alternatives and select an ID.
ASN and city matches are independent; missing ASN, point or radius stays unknown.

Radius uses WGS84 geography and metres (0 < radius <= 20040000). Bounding boxes use
longitude/latitude; west > east crosses the antimeridian, south < north. Boundary
queries select a place boundary from the same dataset snapshot. Area edges are
included. All areas test the **representative point**, not overlap of a provider's
uncertainty disk. Missing radius is null, never zero. A hit means approximate dataset
area context, not precise person/device location or a verified country membership.
No implicit nearest-city inference, point for an unknown place, or stale-point fallback.

## Exact counts, facets and bounds

One SQL statement materializes matched sources once under the shared pipeline lock.
There is at most one fingerprint and one enrichment row per selected source. Candidate
and ASN expansion is confined to facets, with distinct source/endpoint counts:

- `endpoints`: distinct endpoint keys in the complete matched set.
- `observations`: matched source UUIDs, including distinct history with identical bytes.
- `candidates`: sum of all candidate records in the chosen derivations, including
  ambiguity/repeated product values; never equate this with observations or devices.
- Category, ASN, matched ASN prefix, country and geography-state facets report both
  endpoint and observation counts **after all filters**, including their own filter.
  A source/endpoint counts once per bucket. Category/ASN totals can exceed the result
  total; history may put one endpoint in both unknown and known buckets over time.

Counts are exact, not estimates. Unknown buckets are explicit. Facets sort by endpoint
count descending, then value with PostgreSQL C collation; ASN labels sort lexically
on ties. Each facet returns up to `facet_limit` 1–50 (default 20), with `total_buckets`
so truncation is explicit; omitted buckets are not silently merged. Hits sort by
finish/start/UUID descending. `limit` is 1–200 (default 50); `offset` is 0–10000.
Counts/facets cover the full match even for an empty page. No unbounded export exists.

A query statement times out after 5 seconds, with the existing 10-second lock wait.
Exact aggregates still scan broad result sets; row limits do not make their cost
constant. One shared lock serializes search, ingestion, derivation, maintenance and
backup. No concurrency/Internet-scale throughput or public rate-limit claim is made.
The Phase 7 adapter adds separate transport, pagination and local cost/access policy.

## Indexes, replay and removal

Migration 0004 adds nine indexes: inet GiST; port/time and finish/start/UUID B-trees;
fingerprint JSONB GIN and product-label tsvector GIN; enrichment result-choice B-tree,
JSONB GIN, geography GiST and geometry-expression GiST. They index authoritative
immutable rows directly. No asynchronous search copy, extra event consumer, projection
lag, raw-byte duplication or new storage retention policy exists. Existing source FK
indexes and endpoint ordering also participate. Broad queries may prefer sequential
scans; predicate eligibility and actual benchmark plans are checked separately.

Source deletion cascades existing derivations; PostgreSQL updates indexes in the same
transaction. Queries additionally check persistent CIDR suppressions and actual source
expiry before maintenance. Replayed outbox events cannot revive search rows. Rebuilds
use PostgreSQL REINDEX under the operator maintenance lock, followed by source/derivation
`verify`; there is no search data to reconstruct from a separate store. Acceptance
compares results after REINDEX, old/new archive restore and idempotent replay.
0001–0003 are unchanged; 0004 upgrades populated databases without rewriting sources.
Backups include indexes; restoring older archives runs migrations before verification.
The 7-day backup, current-suppression reapplication and independent output-copy handling
rules in STORAGE/SECURITY still apply.

## Evaluation and coverage bias

See [SEARCH_BENCHMARK.md](SEARCH_BENCHMARK.md) for the reproducible local workload,
measured results, index sizes and the evidence-based decision to defer OpenSearch.
Authored tests cover independent exact truth, multiple candidates/ASNs, IPv4/IPv6,
negative/empty/stale sources, version/hash choices, future/expired datasets, missing
points/radii, same names, antimeridian/radius/boundary queries, deterministic ties,
limits, no-clobber output, expiry, suppression/replay, migration and backup restore.

The universe is selected retained synthetic observations, not the Internet. No
estimated global exposure, prevalence, geolocation accuracy or real detection
precision/recall follows from these counts. Vantage, scope, probe timing, retention,
protocol coverage, IPv6 seeds, NAT, anycast, virtual hosts, unknown mappings and
fingerprint spoofing all affect real-world interpretation. Geographic unknowns are
not geographically random missing data. No geographic or category result authorizes
new collection or changes probe budgets.

Primary technical references: [PostgreSQL text indexes](https://www.postgresql.org/docs/18/textsearch-indexes.html),
[JSON operators](https://www.postgresql.org/docs/18/functions-json.html),
and [PostGIS ST_DWithin](https://postgis.net/docs/ST_DWithin.html).

## Phase 7 HTTP adapter

Package 0.8.0 reuses this SQL via a connection adapter under the same lock. Optional
keyset predicates affect the page only; exact counts and facets are unchanged. An
internal cutoff pins cursor measurement/freshness selection while a separate geo
clock rechecks implicit-current dataset validity on every page. Ordinary Phase 6
CLI behavior and private offset contract remain unchanged. Separate allowlisted
HTTP models, signed cursors, typed errors, local policy and generated client are
documented in [API.md](API.md). No raw reads, measurement or geographic UI are added.
