# Architecture

Status: Phase 9 adds source-bound evidence inspection and a retained endpoint timeline
to the geographic explorer and offline MapLibre demonstration over
the bounded local API, indexed PostgreSQL and independent derivations. Only the
modules listed as implemented in `PROJECT_STATE.md` exist today. A monorepo and modular Python package keep early
development small; process/network boundaries are introduced when justified.

## Flow and boundaries

```text
Address sources -> policy/exclusions -> scheduler -> discovery workers
                                                -> protocol collectors
                                                         |
                                              versioned observations
                                                         |
                          bounded spool -> ingestion -> durable history
                                                         |
                 fingerprint/classification + ASN/geo -> derived records
                                                         |
                               current-service projection + search index
                                                         |
                                    read API -> geographic web interface
```

The domain model has no I/O. Collectors depend on domain contracts, not the web
framework or database. Ingestion validates untrusted worker output. Derivations
are versioned and reproducible from evidence. Search is a disposable projection,
not the system of record (the current indexes are directly on authoritative tables). The API never opens a target connection in response to
a search/detail request. The future scan control plane is separate and authenticated.

## Target policy and scheduling

Targets are literal IPv4/IPv6 addresses with source and campaign provenance.
Phase 1 implements explicit addresses/small CIDRs, bounded streaming expansion,
TCP connect discovery, and local JSONL results. Port sets and campaign size are
explicit. No raw socket privileges are required. Exhaustive IPv6 enumeration is
not viable; use documented seeds and routed-prefix sampling later.

Before measurement, policy intersects requested scope with allowed scope and
removes IANA special-purpose/non-global ranges, multicast, operator exclusions,
and opt-outs. `ipaddress.is_global` is one input, not proof of current routing or
permission: Phase 1 pins a conservative collapsed IANA IPv4/IPv6 deny snapshot,
explicit multicast checks, and boundary tests. Runtime classification and IPv6
global-unicast restriction add denials. Routing data is not implemented; later
coverage/enrichment phases will address it. See `docs/DISCOVERY.md` for bounds.
Registry/dataset updates are reviewable maintenance actions, not unpinned network
downloads during tests.
Built-in non-routable restrictions cannot be defeated by a user allowlist.
A narrowly scoped loopback lab mode permits fixture servers; it must not create
a broad private-network bypass. No lab targets may enter production campaigns.

Later scheduling uses deterministic, seeded permutation of eligible targets,
sharded by campaign/worker without duplicate leases. Enforce global, per-node,
and per-prefix (/24 IPv4, /48 IPv6 initially) token budgets. Add endpoint cooldown,
bounded retries with jitter, prefix fairness, job deadlines, expiration, and a
central stop switch. Refresh priorities use age, observed change rate, previous
outcome, coverage goals, and capacity. A timeout is not proof a service vanished.
Global leases must prevent workers multiplying the intended traffic budget.

## Measurement and protocol collectors

Use asyncio task groups, a bounded queue, bounded concurrency, connect and total
interaction timeouts, response byte ceilings, and reliable socket cleanup. Record
configuration hashes and scanner versions. Cancellation flushes completed records
and stops scheduling. Structured error codes separate refused, timed-out, and local
failures; there is no invented service fingerprint for a failed connection.

Discovery records reachability separately from identification. The protocol selection
plan does not consult port numbers. Implemented collectors cover
HTTP, TLS certificates, SSH banners, and SMTP greetings using bounded unauthenticated
interactions. See `docs/PROTOCOL_EVIDENCE.md` for the opt-in two-connection plan,
shared admission callback, cumulative wire/retention accounting and coverage gaps.
HTTP uses bounded requests, no automatic credentials/cookies, no form
submission, no link crawling, no automatic redirect following, and no resource-heavy
paths. TLS probes preserve certificate-chain evidence even for invalid certificates,
without treating their identity assertions as trusted. No SNI or named Host is supported;
literal Host provenance is recorded. An IP's
default virtual host is incomplete coverage. TLS identities are explicitly unverified.

Extend collectors for service/device categories only with documented read-only,
bounded interactions. Database enumeration, camera streams/screenshots, printer
jobs, industrial control actions, and bulk file download are not baseline probes.
UDP is deferred until a protocol-specific safe request/response size budget and
rate limits exist; no broadcast, reflection, amplification, or spoofed-source probes.
Evaluate established discovery/handshake tools (e.g. ZMap/ZGrab2) behind adapters
only when Python throughput is measured to be a bottleneck and the same policy
controls can be preserved. No external scanner adapter is implemented.

`collectors/` depends on config and domain/evidence contracts, not discovery policy,
storage, FastAPI or UI. The engine supplies admission for every connection; passive
syntax parsers implement a small Collector interface and TLS uses an active handshake
adapter. Raw sockets and SSLObject/MemoryBIO give explicit byte accounting and closure.
Configuration v3 leaves protocol collection disabled until explicitly selected. API
health identifies Phase 9; the UI exposes retained synthetic metadata and reviewed previews,
with no measurement controls.

## Evidence and derivations

`docs/DATA_MODEL.md` specifies the current version-2 envelope with an explicit v1
compatibility reader. Append immutable
observations; never overwrite evidence with a later guess. Use an observation UUID
for ingestion idempotency and endpoint identity `(address, transport, port)` for
grouping. TLS/virtual hosts add service dimensions later. Deduplicate bounded raw
content by SHA-256 in the storage adapter; preserve all timestamps and references
even when bytes are shared. Negative results do not erase past positive evidence.

Phase 3 implements `derivations/`: bounded JSON rule packs, a pure engine and an
explicit offline file adapter. Collectors and derivations share only the I/O-free
`protocol_syntax.py` and domain contracts; neither imports the other's execution
layer. Product/category candidates stay separate from immutable observations and
preserve uncertainty and multiple values. No port or protocol-only classification.
Derived records carry source UUID/digest, pack ID/version/digest, engine/taxonomy
version and precise byte selectors/hashes. Reprocessing never mutates observations.
Deterministic records omit wall-clock processing time; later operational ingestion
run metadata may carry it separately. See `docs/FINGERPRINTS.md` for confidence,
taxonomy, compatibility, bounds and replay. No vulnerability or identity proof.

## Storage, ingestion, search, and statistics

Phases 1–3: bounded private JSONL spool under ignored `data/`, atomic campaign manifest,
completed-result flush, final fsync and checksum; no database adapter. Graceful
stops finalize metadata; hard kills may leave a running manifest or partial line.
An advisory spool lock prevents concurrent local campaigns sharing that directory.
Phase 4 implements PostgreSQL with typed endpoint/time/outcome fields and private JSONB
source envelopes, SQLAlchemy transactions and four packaged Alembic migrations. Raw
response/certificate bytes live in a private content-addressed filesystem; exact
JSON-pointer references reconstruct and verify the original v1/v2 canonical source.
Observation UUID plus source digest distinguishes replay from conflict; equal blobs
never collapse distinct measurements. History UPDATE triggers reject silent changes.
Independent pack snapshots and deterministic derivations remain replayable.

The local pipeline serializes writes, reads, GC and backup under one DB advisory
lock. Fsynced blobs precede a synchronous DB commit; acknowledgements follow commit.
Rollback may leave orphans; locked cleanup removes only unreferenced bytes. Projection
and outbox changes share the observation transaction. Current pointers independently
track latest attempt, open connection and nonempty evidence by finish/start/UUID.
A DB consumer commits its idempotent effect and receipt together; external delivery,
distributed leases and a broker remain future work.

Synthetic-only ingestion, private OS/loopback access, 30-day source expiry, whole-record
removal, persisted CIDR suppression and 90-day tombstone/event metadata are implemented.
Expiry/cleanup are explicit operator commands, not a scheduler. Compose and coordinated
PostgreSQL/blob backup/restore drills use a pinned PostgreSQL image. See
[STORAGE.md](docs/STORAGE.md) for exact contracts, access limits and restore/removal
semantics. Phase 5 adds PostGIS and independent enrichment snapshots/results without
rewriting observations. No real-data ingestion or search cluster is enabled;
partitions/object storage await demonstrated scale requirements.

Phase 6 implements `search/` with bounded local JSON query/output, structured filters,
product-label full-text search and PostGIS radius/box/boundary predicates. Queries
select current attempt/open/evidence or retained history before applying filters.
Exact counts distinguish endpoints, observations and candidates; facets deduplicate
per source/endpoint and state truncation. Pack/dataset hashes and engines are explicit;
current queries check dataset validity again. Historical as_of never bypasses actual
source expiry or suppression. Read [SEARCH.md](docs/SEARCH.md) for precise semantics.

Migration 0004 indexes authoritative rows directly: no asynchronous search projection,
consumer, index lag or copied raw content. One query runs under the shared maintenance
lock with a 5-second statement ceiling. Deletion updates indexes transactionally;
REINDEX, populated upgrades and backup/restore preserve query results. The bounded
synthetic benchmark in [SEARCH_BENCHMARK.md](docs/SEARCH_BENCHMARK.md) supports deferring
OpenSearch. Broad exact aggregates remain proportional to the matched set; worldwide
throughput, concurrent service operation and public API cost limits are unqualified.

## Enrichment and geographic UI

Phase 5 implements `enrichment/`: I/O-free dataset/result contracts, pure independent
ASN/city longest-prefix matching and exact name gazetteer disambiguation. Bounded
offline adapters verify file checksums and publish private results; they never fetch
or measure. Origins preserve license/attribution, source/version/checksum and changes.
Unknown/stale/not-yet-valid datasets yield explicit unknowns. Reproducibility includes
an explicit evaluation clock; current queries separately filter dataset expiry.

`storage/enrichment.py` persists canonical snapshots, source-linked independent
results and gazetteer projections in the existing locked transaction/outbox protocol.
Migration 0003 creates PostGIS, WGS84 geography points and geometry MultiPolygons.
Points support metre-aware distances; boundaries require antimeridian splitting and
valid topology. Optional provider radii remain unknown when absent. Place IDs, not
name equality or nearest centroids, supply associations. Geographic context never
locates a person/device precisely or establishes country membership of a device.

A pinned Natural Earth 5.1.2 subset (Suva/Fiji) supplies real public-domain places and
generalized boundary data in the offline demo. Its IP/ASN associations are fictional
documentation fixtures. DB-IP Lite/GeoNames license terms were reviewed, but their
datasets were not imported; global routing/geo import/coverage remains unimplemented.
All downloads/outputs remain ignored. Details, provenance and commands are in
[ENRICHMENT.md](docs/ENRICHMENT.md).

Enrichment UPDATE triggers, cascade removal, orphan snapshot cleanup and replay
verification extend existing retention/restore. Spatial backup restore and populated
Phase 4 archive upgrade are tested. Phase 6 now supplies local search indexes/filters/facets;
Phase 7 exposes bounded metadata read routes; Phase 8 now implements the geographic UI.

React/TypeScript now uses MapLibre with a reviewed tiny offline Fiji GeoJSON outline,
local module worker, no tiles/glyphs/external fonts and a complete accessible list.
The map clusters only the displayed observation page; exact API totals are separate.
Source/dataset/pack identities, multiple candidates/ASNs and unknown radii remain
explicit. Place lookup uses stable-ID disambiguation and country/association/boundary
predicates without remote geocoding. The single read lane aborts obsolete work and
rejects stale responses. Each page replaces the prior view; hidden or 60-second-old
views are cleared. No persistent result cache or instant push-removal guarantee.
`netatlas.demo` is a separate explicit operator fixture seed, unreachable from reads.
See [GEOGRAPHIC_UI.md](docs/GEOGRAPHIC_UI.md) and [MAP_ASSETS.md](docs/MAP_ASSETS.md).

Phase 9 implements pure `inspection/` models/projection, a source-bound storage reader,
and a separate read-transport orchestrator. Exact endpoint/UUID/digest and optional
source-bound derivation IDs gate reconstruction under the existing lock. Actual
expiry/suppression is checked before and after projection. Bounded UTF-8 text and
certificate assertions use a versioned, ephemeral minimization policy separate from
canonical evidence. No arbitrary file/blob/URL reads or raw downloads exist.

The UI shows all retained attempts in a one-page timeline and inspects one immutable
source at a time. Exact trace slices/hashes are checked without rerunning rules.
Cryptography parses whole bounded DER only; verification remains not_performed.
No certificate/resource fetches, active HTML, images or captured links. Withheld
headers, recognized sensitive-marker redaction and explicit unsupported formats are
not comprehensive sanitization; synthetic-only ingestion remains mandatory.
See [INSPECTION.md](docs/INSPECTION.md) for exact limits and failure semantics.

## API, observability, and deployment

FastAPI retains `/healthz` (process liveness, not DB readiness), the static synthetic
example and OpenAPI. Phase 7 adds POST search/facets/places/endpoint detail/history.
`read_api/` owns explicit allowlisted transport models, signed query-bound keysets,
metadata projection, error and local access/cost policy; `search/` owns SQL and
selection semantics. The search connection adapter reuses the shared lock/snapshot.
No source envelopes, arbitrary blob reads, collection or enrichment execution is reachable.
The inspection route alone performs reviewed source-bound reconstruction and projection.

Cursors pin a measurement cutoff and expire after 15 minutes; actual source retention
and implicit-current dataset validity are rechecked per page. Counts/facets cover
the full matched set; continuation applies only to hits. There is no cross-request
snapshot or cached result set. Exact totals can change with retained data. The
HTTP offset is fixed at zero and traversal stops at 10000 hits.

Loopback peers/Host/Origin, required read header, no forwarded trust/CORS and one
in-flight data request provide a trusted-local synthetic demonstration boundary.
Streaming body/time bounds, DB timeouts, escaped bounded JSON and generic errors
limit cost/exposure. These are not public authentication, field-level sensitive-data
sanitization or production roles. OpenAPI generates the TypeScript client contract;
make check rejects drift. See [API.md](docs/API.md).

Discovery emits redacted JSON logs with generated campaign/observation IDs,
outcomes and completion counts. Scope/contact/raw exceptions stay out of these logs.
The API still omits request access logs. Later add job IDs and operational metrics;
Prometheus-compatible metrics for rates, queue depth, failures, latency, coverage,
ingestion/index lag, and resource use; optional OpenTelemetry traces. No raw IP or
endpoint labels in metrics: cardinality and privacy would be unacceptable at scale.

Validated TOML supplies reproducible non-secret configuration; hash effective
settings per run. Later secrets use environment/secret stores and never enter the
configuration digest payload or logs. Save policy/dataset versions and seed along
with configuration. Tests use synthetic data, deterministic clocks, loopback
fixtures, controlled load, and documented benchmark workloads.

The API/geographic UI runs as two local processes. Phase 5 extends Compose with a native arm64/amd64 PostGIS build on the pinned
PostgreSQL 18.3 base and pinned PostGIS packages. The deployment path is containers, a same-origin TLS reverse
proxy, internal data services, and separated worker/control-plane networks. Worker
authentication, lease heartbeats, retry semantics, and backpressure precede multi-node
operation. Reproducibility includes runtime pins, dependency locks, CI, migrations,
and fixture datasets. A local synthetic database/blob restore drill is tested; production deployment,
failover and distributed recovery remain future acceptance criteria.

## Capacity and thesis validity

No assumed Internet-wide throughput target is promised. Model address count ×
ports × revisit frequency, average response bytes, retry budget, storage retention,
and worker bandwidth; measure each phase against local budgets. Document IPv4/IPv6
and protocol coverage gaps, vantage bias, IP churn, NAT, anycast, virtual hosting,
geolocation error, and the distinction between reachable exposure and vulnerability.
Worldwide continuous operation has real bandwidth, infrastructure, and staffing
costs even when all software and demonstration data are free.
