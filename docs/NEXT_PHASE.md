# PHASE 6 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
Complete exactly Phase 6 in this fresh Work chat; do not begin Phase 7.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md, SECURITY.md, docs/DATA_MODEL.md, docs/STORAGE.md, docs/ENRICHMENT.md,
docs/DISCOVERY.md, docs/PROTOCOL_EVIDENCE.md and docs/FINGERPRINTS.md first. Inspect
Git status/remotes, toolchains, code and tests. Repository files are authoritative.
Respect user changes; make routine engineering decisions without approval gates.

Phase 5 delivered package 0.6.0 on Python 3.14/FastAPI/Pydantic and a React/TypeScript/
Vite shell. Config v3; observations/manifests v2 with explicit v1 reads; fingerprint
pack/result schemas v1, engine fingerprints-1, taxonomy netatlas-categories-1;
enrichment dataset/result schemas v1, engine enrichment-1; Alembic head 0003.
Storage is PostgreSQL 18.3/PostGIS 3.6.4 with SQLAlchemy/psycopg.

Discovery remains bounded literal IPv4/IPv6/small CIDRs with pinned policy,
exclusions/opt-outs, shared pacing, deadlines/cancellation and private spool.
CLI defaults dry-run; enabled operator identity and --measure are required.
Protocol evidence additionally requires measurement.protocol_evidence = true.
Lab permits only literal 127.0.0.1/::1. Budgets remain two connections, two GET /
requests and one TLS handshake per endpoint. No DNS/SNI, redirects, cookies,
authentication, mail, STARTTLS or device commands. No Internet campaign has run.

Fingerprints remain independent immutable derivations with source/pack hashes,
engine/taxonomy versions and exact decoded-byte selectors/hashes. The core has four
nginx/OpenSSH/Postfix assertion rules; broader device classes have fictional coverage
only. Preserve unknowns/multiple candidates and ordinal asserted/corroborated confidence.

Synthetic-only local storage preserves original v1/v2 sources through private raw
blobs, hash-placeholder JSONB and evidence_refs. UUID plus canonical digest distinguishes
replay/conflict; distinct history survives deduplication. Fsynced files precede
synchronous commits; acknowledgements follow each row's commit. Current pointers
independently select last attempt/open/nonempty evidence by finish/start/UUID.
Negative/stale/empty attempts preserve evidence. One advisory lock covers pipeline
operations/GC. Transactional outbox and same-DB consumer receipts support cursor
replay; derivation events cover both fingerprints and enrichment at source granularity.

Enrichment is pure offline independent ASN/city longest-prefix matching, separate
IPv4/IPv6 families, stable-ID gazetteer and explicit uncertainty. Dataset files require
exact SHA-256; results preserve canonical dataset/source hashes, versions, attribution,
license, matching prefixes and explicit evaluated_at. Missing radius stays unknown.
Stale/not-yet-valid bundles yield unknowns. Historical replay uses its recorded clock;
current searches MUST also check dataset expiry at query time, plus source expiry.
PostGIS stores WGS84 geography points and split geometry MultiPolygon boundaries.
Same-name places retain alternatives. Never infer precise person/device location.

The normalized bundle is bounded to 2 MiB and 4096 rows per collection, using linear
prefix matching. Natural Earth v5.1.2 Suva/Fiji is the small public-domain demo;
its IP/ASN associations are fictional documentation fixtures. Downloads/generated
subsets stay ignored. DB-IP Lite/GeoNames terms were reviewed but neither was imported.
No global geo/routing coverage, paid service, downloader or automatic refresh exists.

Sources expire after 30 days. Reads reject expiry; explicit maintenance removes
history/derivations/projections and unused snapshots/blobs. Persistent CIDR suppression
blocks ingestion and removes matching records. Tombstones/removed-source events last
90 days. Spools/downloads/offline outputs/backups require separate handling. Backup
policy is 7 days; older restores require current suppressions before use. Phase 4
archives migrate to 0003 before expiry/replay; spatial backup/restore is tested.
No real ingestion, public raw display, field sanitizer, encryption or production
service-role isolation exists. Preserve these boundaries in new query projections.

Runtime pins: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0. TLS tests require
OpenSSL and temporary keys. Inspect Docker/Compose/Colima availability. The dedicated
Colima netatlas profile may need restarting. Run make db-up COMPOSE=docker-compose,
then make db-migrate; Compose-plugin hosts omit the override. The native arm64/amd64
PostGIS Docker build keeps the existing PostgreSQL base/volume/secret and pins direct
extension packages, but not all transitive APT packages. Do not discard existing data.
make check-db runs the full make check with PostgreSQL enabled; plain make check
skips DB tests without NETATLAS_TEST_DB=1. CI requires check-db. Phase 5 passed 212
Python/3 web tests, lint/types/builds, offline demo and DB migration/restore checks.
Verify current results rather than treating historical counts as fresh validation.

Implement Phase 6 — Search and Aggregate Statistics: indexed PostgreSQL structured,
text and geographic filtering, freshness/history filters, category/network facets
and explicit count semantics. Keep storage/search separate from collection/domain,
with a bounded local interface and reproducible synthetic workload. Distinguish
unique endpoints from observations and derivation candidates; prevent join-driven
double counting. Define current versus historical selection, dataset/pack/version
choice, unknowns, stale evidence and coverage bias. Preserve deletion, suppression,
expiry, deterministic ordering and rebuild/replay guarantees. Add reviewed migrations
for justified indexes/projections and verify backup/restore compatibility.

Acceptance: compare query/facet/count results with authored fixture truth; include
IPv4/IPv6, ambiguous fingerprints, unknown/stale geography, antimeridian/radius areas,
same-name places, historical observations and removed sources. Report measured
latency and index size for a documented synthetic workload and environment. Decide
from evidence whether optional OpenSearch is justified; do not add it by default.
Do not implement Phase 7 HTTP read routes or Phase 8 geographic UI.

Never add credential guessing, bypass, exploitation, persistence, remote modification
or destructive actions. Do not enlarge probe scope/budgets, use Internet smoke targets
or commercial discovery databases. No release/tag. Ask only for genuine blockers,
credentials, permissions or unavoidable manual actions after independent work.

At completion run relevant checks and make check with DB integration enabled; update
authoritative docs with actual state/results/limitations; replace NEXT_PHASE with a
self-contained Phase 7 kickoff. Review tracked files/diff for secrets, captures and
generated data. Commit with a Phase 6 message, push, verify local HEAD equals remote
delivery HEAD and the tree is clean. Report checks, commit, push/CI, blockers, exact
current state and the complete Phase 7 kickoff, then stop.
