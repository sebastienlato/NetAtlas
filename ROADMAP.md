# Roadmap

Exactly one phase per fresh Work chat. Keep each phase a bounded vertical increment;
if evidence makes a phase too large, update this roadmap before implementation with
a meaningful split. Every phase closes with appropriate checks, updated state/docs,
a reviewed commit, push/remote verification when possible, and a self-contained next
kickoff. Real Internet campaigns are never implicit test fixtures.

| Phase | Delivery | Acceptance / scope boundary |
| --- | --- | --- |
| **0 — Foundation and architecture (complete)** | Repository, domain/config contracts, CLI/API/web entry points, CI, authoritative docs. | Locked setup, tests/static checks/build/smoke pass; no scanner. |
| **1 — Bounded discovery engine (complete)** | Explicit literal IPv4/IPv6 targets and small CIDRs; TCP connect worker; exclusions; streaming target handling; global/per-prefix rate control; timeout/cancellation; JSONL spool and manifest. | Loopback fixture confirms open/refused/timeout/error semantics; policy rejects non-global/multicast/opt-out targets outside narrow lab mode; bounded memory/queue/size; CLI dry-run default, operator identity required for enabled runs. No protocol collectors or public sweep. |
| **2 — Protocol evidence (complete)** | HTTP, TLS, SSH, SMTP collector interface and implementations; bounded raw capture; handshake-based protocol identification. | Synthetic fixture services including malformed/slow/oversized responses; cancellation and cleanup; no redirects/credentials/state-changing actions; protocol independent of conventional port. |
| **3 — Fingerprints and categories (complete)** | Versioned deterministic rule packs; evidence/confidence; taxonomy covering planned device types with honest unknown results. | Small labeled synthetic corpus, ambiguity/false-positive checks and reprocessing; categories do not imply every device type is detectable. No exploit/vulnerability confirmation. |
| **4 — Durable observation pipeline** | PostgreSQL schema/migrations, ingestion, content-addressed blobs, history/current-service views, deduplication, outbox, local Compose setup. | Duplicate/reordered input, transactional failure/replay, upgrade migration, basic backup/restore, and data retention tests. No search cluster required. |
| **5 — Network and geographic enrichment** | Versioned offline ASN/prefix and approximate city lookup, place gazetteer, PostGIS points/boundaries, attribution metadata. | Unknowns, IPv4/IPv6 prefix matching, bad/stale datasets, location uncertainty, antimeridian and same-name place fixtures; demonstrate with a small freely usable dataset. |
| **6 — Search and aggregate statistics** | Indexed PostgreSQL filters/text/geo search, freshness and history filters, category/network facets, count semantics. | Reproducible synthetic workload with reported latency/index size; compare correctness to fixture truth; decide whether optional OpenSearch is justified. |
| **7 — Read API** | Search/facets/places/endpoint history/detail routes, OpenAPI client contract, pagination and query limits. | API contract/integration tests, stable errors/cursors, cost limits and basic access policy; API cannot initiate scans. |
| **8 — Geographic exploration UI** | Country/region/city search, results list and MapLibre clusters, categorized filters, accessible navigation and offline demonstration map. | End-to-end representative searches, responsive UI, place disambiguation, attribution, uncertainty display, loading/error/empty states. |
| **9 — Service and evidence inspection** | Endpoint timeline, protocol fields, certificates, confidence/evidence trace, escaped bounded content previews. | Hostile content cannot execute or load external resources; redaction and retention policy enforced; detail views link measurements and derivation versions. |
| **10 — Distributed measurement** | Two local/containerized workers, authenticated registration, durable leases/heartbeats, ingestion backpressure, retry/idempotency. | Worker failure/restart and duplicate delivery drills; centrally budgeted rates; no requirement for paid infrastructure or a real global campaign. |
| **11 — Coverage and refresh scheduling** | Reproducible routed-space sampling/sharding, IPv6 seed policy, prefix fairness, stale-service refresh priorities, opt-out propagation and stop controls. | Small synthetic address universe demonstrates coverage, schedule determinism, expiration and global budgets. Evaluate one bounded UDP collector only if its protocol budget and fixture evidence fit this phase; otherwise explicitly defer it. |
| **12 — Operational hardening** | Structured telemetry, dashboards, readiness, bounded resource use, secrets/access control, reproducible deployment and retention/restore runbook. | Controlled load/failure exercise, backups/restores, authenticated control plane, opt-out handling, dependency review, deployment smoke test. |
| **13 — Thesis evaluation** | Reproducible benchmark and labeled evaluation corpus; precision/recall, latency, throughput, storage growth, freshness, geography/coverage bias report. | Repeatable scripts, configuration/dataset provenance and uncertainty; any real-world measurement scope is separately documented and explicitly authorized, with institutional requirements resolved. |
| **14 — Thesis-ready demonstration/release** | Seeded offline end-to-end demonstration, install/deploy docs, architecture/evaluation evidence, release checklist and presentation-ready material. | Fresh-machine rehearsal, reproducible demo, documented limitations and costs, owner/university publication/license decisions, clean release commit; tag/release only here when authorized. |

The final thesis-ready product must discover its own services and support search,
map exploration, safe inspection, history, and reproducible evaluation. A local
demonstration of distributed behavior does not establish worldwide continuous
deployment, complete Internet coverage, or correctness for every device category.
