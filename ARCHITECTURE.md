# Architecture

Status: accepted Phase 0 direction. Only the modules listed as implemented in
`PROJECT_STATE.md` exist today. A monorepo and modular Python package keep early
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
not the system of record. The API never opens a target connection in response to
a search/detail request. The future scan control plane is separate and authenticated.

## Target policy and scheduling

Targets are literal IPv4/IPv6 addresses with source and campaign provenance.
Phase 1 begins with explicit addresses/small CIDRs, bounded streaming expansion,
TCP connect discovery, and local JSONL results. Port sets and campaign size are
explicit. No raw socket privileges are required. Exhaustive IPv6 enumeration is
not viable; use documented seeds and routed-prefix sampling later.

Before measurement, policy intersects requested scope with allowed scope and
removes IANA special-purpose/non-global ranges, multicast, operator exclusions,
and opt-outs. `ipaddress.is_global` is one input, not proof of current routing or
permission: maintain versioned IANA IPv4/IPv6 registry snapshots, routing data,
explicit multicast checks, and boundary tests. Registry/dataset updates are
reviewable maintenance actions, not unpinned network downloads during tests.
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

Discovery records reachability separately from identification. Port numbers are
hints, never sufficient identification evidence. Initial collectors will cover
HTTP, TLS certificates, SSH banners, and SMTP greetings using standard unauthenticated
handshakes. HTTP uses bounded requests, no automatic credentials/cookies, no form
submission, no link crawling, no automatic redirect following, and no resource-heavy
paths. TLS probes preserve certificate-chain evidence even for invalid certificates,
without treating their identity assertions as trusted. SNI/Host names require
separate provenance; an IP's default virtual host is incomplete coverage.

Extend collectors for service/device categories only with documented read-only,
bounded interactions. Database enumeration, camera streams/screenshots, printer
jobs, industrial control actions, and bulk file download are not baseline probes.
UDP is deferred until a protocol-specific safe request/response size budget and
rate limits exist; no broadcast, reflection, amplification, or spoofed-source probes.
Evaluate established discovery/handshake tools (e.g. ZMap/ZGrab2) behind adapters
only when Python throughput is measured to be a bottleneck and the same policy
controls can be preserved. Do not launch external scanners in Phase 0.

## Evidence and derivations

`docs/DATA_MODEL.md` specifies the current version-1 envelope. Append immutable
observations; never overwrite evidence with a later guess. Use an observation UUID
for ingestion idempotency and endpoint identity `(address, transport, port)` for
grouping. TLS/virtual hosts add service dimensions later. Deduplicate bounded raw
content by SHA-256 in the persistence phase; preserve all timestamps and references
even when bytes are shared. Negative results do not erase past positive evidence.

Fingerprint rules have identifiers, versions, confidence, and evidence references.
Separate product detection from device category, allow multiple classifications,
and retain unknown results and conflicting evidence. Do not equate a product match
with a confirmed vulnerability. Derived records include rule/dataset versions and
processing time; reprocessing must not mutate original observations.

## Storage, ingestion, search, and statistics

Phase 1: bounded JSONL spool under ignored `data/`; no fake database adapter.
Phase 4: PostgreSQL is authoritative, with typed endpoint/network fields, JSONB
for protocol-specific attributes, migrations via Alembic/SQLAlchemy, and immutable
observation rows. Add PostGIS for geographic points/radius/bounding-box queries.
Keep raw blobs on local content-addressed disk for a small deployment and behind
an object-storage interface for scale. Use time-based partitions, retention, index
size monitoring, and explicit backup/restore procedures as volume justifies them.

Ingestion uses validation, schema version checks, idempotent observation IDs,
transactions, dead-letter/quarantine handling, and acknowledgments only after
durable commit. A transactional outbox makes index/derivation delivery recoverable.
Start with in-process work and database job leases. Introduce a broker only after
measured backlog/coordination requires it; do not deploy Kafka or Kubernetes early.

Search starts with PostgreSQL indexed structured filters, full-text search, and
PostGIS. Add OpenSearch as an optional horizontally scalable denormalized index
after benchmarks justify the operational cost. Index rebuilds must be possible
from authoritative data. Current-service views track last successful observation,
last attempt, freshness, and index lag separately. Statistics count unique endpoints
and observations separately, state time windows, and include sampling/coverage bias.

## Enrichment and geographic UI

Prefer freely downloadable, license-compatible datasets. Candidate sources include
RIPE RIS/Route Views for routing/ASN and DB-IP Lite for approximate city placement;
evaluate exact release/license, freshness, checksum, and attribution in Phase 5.
GeoLite2 is optional because its acquisition requires registration/license acceptance.
Do not bake a dataset whose terms have not been checked into the repository.
Support unknown locations, stale mappings, missing city data, and accuracy radius.
An IP location does not locate the person, device, or street address with certainty.

Use a freely usable offline place gazetteer for country/region/city lookup, with
disambiguation for same-name places, administrative codes, and bounding areas.
Coordinates use WGS84. Radius queries use meter-aware PostGIS geography operations;
bounding boxes must handle the antimeridian. City/country membership should use
dataset identifiers or boundaries, not string equality or rounded coordinates alone.

React/TypeScript uses MapLibre for maps in Phase 8. Local/self-hosted tiles or a
small offline regional basemap keep the demonstration independent of paid maps.
OpenStreetMap attribution and tile-provider terms must be respected; public OSM
tile servers are not an unrestricted production CDN or bulk-download endpoint.
The UI will show categorized markers/clusters, facets, time/freshness controls,
and accessible list alternatives. Uncertainty and absent data stay visible.

Service inspection shows sanitized metadata, escaped text/hex, certificates, and
bounded response previews. Never execute returned HTML/scripts, automatically
embed remote images, or open captured URLs. Sensitive content requires redaction,
access control, retention rules, and an operator removal workflow before real ingestion.

## API, observability, and deployment

FastAPI exposes typed versioned JSON contracts. Phase 0 has `/healthz` (process
liveness only), `/api/v1/examples/observation`, and generated OpenAPI; later phases
add bounded queries, cursor pagination, validation, caching, authorization, and
query cost/rate limits. Liveness and readiness become distinct once dependencies
exist. No permissive CORS is needed: the development proxy is same-origin.

Phase 0 uses ordinary Python logging without request access logs or response bodies.
Later use structured logs with campaign/job IDs, stable error codes, and redaction;
Prometheus-compatible metrics for rates, queue depth, failures, latency, coverage,
ingestion/index lag, and resource use; optional OpenTelemetry traces. No raw IP or
endpoint labels in metrics: cardinality and privacy would be unacceptable at scale.

Validated TOML supplies reproducible non-secret configuration; hash effective
settings per run. Later secrets use environment/secret stores and never enter the
configuration digest payload or logs. Save policy/dataset versions and seed along
with configuration. Tests use synthetic data, deterministic clocks, loopback
fixtures, controlled load, and documented benchmark workloads.

Local Phase 0 runs as two processes. Phase 4 introduces Compose for local database
services when needed. The deployment path is containers, a same-origin TLS reverse
proxy, internal data services, and separated worker/control-plane networks. Worker
authentication, lease heartbeats, retry semantics, and backpressure precede multi-node
operation. Reproducibility includes runtime pins, dependency locks, CI, migrations,
and fixture datasets. Deployment and restore tests are future acceptance criteria,
not claims about this skeleton.

## Capacity and thesis validity

No assumed Internet-wide throughput target is promised. Model address count ×
ports × revisit frequency, average response bytes, retry budget, storage retention,
and worker bandwidth; measure each phase against local budgets. Document IPv4/IPv6
and protocol coverage gaps, vantage bias, IP churn, NAT, anycast, virtual hosting,
geolocation error, and the distinction between reachable exposure and vulnerability.
Worldwide continuous operation has real bandwidth, infrastructure, and staffing
costs even when all software and demonstration data are free.
