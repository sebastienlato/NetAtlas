# PHASE 7 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
Complete exactly Phase 7 in this fresh Work chat; do not begin Phase 8.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md, SECURITY.md, docs/DATA_MODEL.md, docs/STORAGE.md, docs/ENRICHMENT.md,
docs/SEARCH.md, docs/SEARCH_BENCHMARK.md, docs/DISCOVERY.md,
docs/PROTOCOL_EVIDENCE.md and docs/FINGERPRINTS.md first. Inspect Git status/remotes,
toolchains, code and tests. Repository files are authoritative. Respect user changes;
make routine engineering decisions autonomously, without approval gates.

Phase 6 delivered package 0.7.0 on Python 3.14/FastAPI/Pydantic and a React/TypeScript/
Vite shell. Config v3; observation/manifest v2 with explicit v1 reads; fingerprint
pack/result schemas v1, engine fingerprints-1, taxonomy netatlas-categories-1;
enrichment bundle/result schemas v1, engine enrichment-1; local query schema v1;
Alembic head 0004. PostgreSQL 18.3/PostGIS 3.6.4, SQLAlchemy/psycopg. No stored-data
HTTP routes, geographic UI, public deployment or Internet campaign exists.

Discovery stays bounded literal IPv4/IPv6/small CIDRs with pinned policy,
exclusions/opt-outs, shared pacing, deadlines/cancellation and private spool.
CLI defaults dry-run; enabled operator identity and --measure required.
Protocol evidence additionally requires measurement.protocol_evidence=true.
Lab allows only literal 127.0.0.1/::1. Budgets: two connections, two GET / requests,
one TLS handshake per endpoint. No DNS/SNI, redirects, cookies, authentication,
mail, STARTTLS, crawling or device commands. TCP-open differs from protocol success.

Fingerprints are independent immutable derivations with source/pack hashes,
engine/taxonomy versions and exact decoded-byte selectors/hashes. Core has four
nginx/OpenSSH/Postfix assertion rules; broader device classes have fictional coverage
only. Preserve unknowns, multiple candidates and ordinal asserted/corroborated
confidence. Never infer authenticated identity, physical devices or vulnerabilities.

Synthetic-only local storage preserves original v1/v2 sources through private raw
blobs, hash-placeholder JSONB and evidence_refs. UUID plus canonical digest distinguishes
replay/conflict; separate history survives deduplication. Fsynced files precede
synchronous commits; acknowledgements follow each row's commit. Independent current
attempt/open/nonempty-evidence pointers order by finish/start/UUID. Negative/stale/
empty attempts preserve prior evidence. One advisory lock covers pipeline operations,
search, GC and backup. Transactional outbox and same-DB receipts support cursor replay;
derivation events cover both fingerprint and enrichment changes at source granularity.

Enrichment is pure offline independent IPv4/IPv6 ASN/city longest-prefix matching,
stable-ID gazetteer and explicit uncertainty. Files require exact SHA-256; results
retain canonical source/dataset hashes, versions, attribution/licenses, matching
prefixes and explicit evaluated_at. Missing radius stays unknown. Stale/future bundles
yield unknowns. PostGIS stores WGS84 geography points and split geometry MultiPolygon
boundaries with holes; invalid topology fails. Same-name places retain separate IDs.
Never infer precise person/device location or verified country membership.

Bundles are bounded to 2 MiB and 4096 rows per collection, with linear prefix lookup.
Natural Earth v5.1.2 Suva/Fiji is the small public-domain demo; IP/ASN associations are
fictional documentation fixtures. Downloads/generated subsets remain ignored. DB-IP
Lite/GeoNames terms were reviewed but neither imported. No global geo/routing coverage,
paid service, downloader or automatic refresh exists.

Phase 6 search is a separate local module/CLI with indexed structured, product-label
text and geographic filtering, freshness/history, and exact aggregate counts. Current
attempt/open/evidence selection happens BEFORE filters; no older-match fallback.
History selects all eligible sources. Pack hash (default core), dataset hash (default
disabled), engine/taxonomy and latest evaluation at/before as_of are explicit. No
arbitrary newest dataset/pack, merged engines or cross-source derivation claims.
Text is simple-token AND matching over product labels only; no raw banner/header/body/
certificate/URL index. Radius/box/boundary filters test representative points, not
provider-uncertainty-disk overlap. Keep unknowns and radius/attribution metadata visible.

Queries ALWAYS check actual source expiry and persistent CIDR suppression, including
historical as_of. Current queries also check dataset validity at query time; earlier
valid enrichments cannot remain fresh forever. Historical queries describe retained
measurements, not operator knowledge at historical ingestion time. Later derivations,
retention/deletion and writes can change pages. Exact counts distinguish endpoint keys,
source UUIDs and all selected derivation candidates. Category/ASN/prefix/country/geo
facets deduplicate per source/endpoint; multi-valued/history buckets can exceed totals.
Facets are post-filter, including their own filter, with total_buckets indicating
truncation. Do not expose counts as Internet prevalence or physical-device counts.

Migration 0004 adds nine indexes directly to immutable tables: inet GiST; port/time
and finish/start/UUID B-trees; JSONB/tsvector GIN; enrichment choice B-tree; JSONB GIN;
geography and geometry-expression GiST. There is no asynchronous search copy/consumer,
index lag or eventual deletion. REINDEX, replay, populated upgrades and backup/restore
preserve results. The benchmark uses 2048 synthetic endpoints/6144 sources with exact
counts/facets, 20 warm samples/query; see SEARCH_BENCHMARK for final timings and sizes.
It supports deferring OpenSearch, not worldwide or concurrent capacity claims.

The local query contract bounds 16 KiB JSON, 256-character text, 1–200 hits, offset
0–10000, 1–50 buckets/facet, bounded areas and a 5-second statement timeout. The shared
lock wait is 10 seconds. CLI prints only counts; detailed escaped JSON is private,
no-clobber output under ignored data/ (4 MiB maximum). Pack/dataset metadata includes
attribution/license and version provenance. These private dictionaries/offsets are NOT
a reviewed HTTP contract or a field-level sanitizer. No raw blobs are read by search.

Sources expire after 30 days. Reads reject expiry; explicit maintenance removes
history/derivations/projections and unused snapshots/blobs. Persistent CIDR suppression
blocks ingestion and removes matching records. Tombstones/removed-source events last
90 days. Spools/downloads/offline/search outputs/backups require separate removal.
Backup policy is 7 days; older restores require current suppressions before use.
Old archives migrate through 0004 before expiry/replay. Spatial/search restore is tested.
No real ingestion, public raw display, field sanitizer, encryption or production
service-role isolation exists. Preserve these boundaries in API responses.

Runtime pins: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0. TLS tests need OpenSSL
and ephemeral keys. Inspect Docker/Compose/Colima. Dedicated Colima netatlas may need
restarting. Run make db-up COMPOSE=docker-compose, then make db-migrate; Compose-plugin
hosts omit the override. Native arm64/amd64 PostGIS build preserves the existing
PostgreSQL base/volume/secret and pins direct extension packages, not all transitive
APT packages. Do not discard existing data. make check-db runs full make check with
NETATLAS_TEST_DB=1; plain make check skips DB tests otherwise. CI requires check-db.
Phase 6 passed 240 Python/3 web tests, lint/types/builds, CLI smoke, synthetic benchmark
and migration/restore checks. Verify current results rather than reusing old counts.

Implement Phase 7 — Read API: bounded search/facets/places/endpoint history/detail
routes, typed OpenAPI client contract, stable pagination/query limits and errors,
and a documented basic access policy. Keep API separate from search/storage/domain
and collectors. Reuse Phase 6 semantics rather than reinterpreting clocks, counts,
unknowns, derivation choices or geographic precision. Decide routine route/contract/
cursor choices from evidence and document them. Add integration/contract tests with
synthetic PostgreSQL fixtures, cost/input bounds, deterministic pagination, stale/
unknown/ambiguous data, deletion/expiry/suppression and hostile metadata. API requests
must NEVER initiate scans, DNS, enrichment downloads or other target interactions.
Keep raw captures private; evidence inspection UI is Phase 9. Do not implement Phase 8
geographic UI or expand collection. Update shell/status only to describe actual delivery.

Never add credential guessing, authentication bypass, exploitation, persistence,
remote modification or destructive actions. Do not enlarge probe budgets, use Internet
smoke targets or commercial discovery databases. No release/tag. Ask only for genuine
blockers, credentials, permissions or unavoidable manual actions after independent work.

At completion run relevant checks and make check with DB integration enabled; update
authoritative docs with actual state/results/limitations; replace NEXT_PHASE with a
self-contained Phase 8 kickoff. Review tracked files/diff for secrets, captures and
generated data. Commit with a Phase 7 message, push, verify local HEAD equals remote
delivery HEAD and the tree is clean. Report checks, commit, push/CI, blockers, exact
current state and the complete Phase 8 kickoff, then stop.
