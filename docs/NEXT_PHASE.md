# PHASE 9 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
Complete exactly Phase 9 in this fresh Work chat; do not begin Phase 10.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md, SECURITY.md, docs/API.md, docs/DATA_MODEL.md, docs/STORAGE.md,
docs/ENRICHMENT.md, docs/SEARCH.md, docs/SEARCH_BENCHMARK.md, docs/GEOGRAPHIC_UI.md,
docs/MAP_ASSETS.md, docs/DISCOVERY.md, docs/PROTOCOL_EVIDENCE.md and
docs/FINGERPRINTS.md first. Inspect Git status/remotes, toolchains, code/tests and
the current web explorer/client. Repository files are authoritative. Respect owner
changes and make routine engineering decisions autonomously without approval gates.

Phase 8 delivered package 0.9.0, HTTP/local query schemas 1, config 3,
observation/manifest 2 with explicit v1 reads; fingerprint pack/result 1, engine
fingerprints-1, taxonomy netatlas-categories-1; enrichment bundle/result 1, engine
enrichment-1; Alembic head 0004. Python 3.14/FastAPI/Pydantic, PostgreSQL 18.3/PostGIS
3.6.4, SQLAlchemy/psycopg and React/TypeScript/Vite/MapLibre 6.12.0 are implemented.
No evidence viewer, public deployment, real-data ingestion or Internet campaign
exists. OpenSearch remains deferred by the small local synthetic benchmark.

Implement Phase 9 — Service and evidence inspection: endpoint timeline, protocol
fields, certificates, confidence/evidence trace and escaped bounded content previews.
Acceptance: hostile content cannot execute or load external resources; redaction and
retention policy is enforced; detail views link measurements and derivation versions.
Keep UI, read transport, search, storage, derivations, domain and collectors separable.
Do not expand collection, introduce distributed workers or begin Phase 10.

The existing detail/history API exposes allowlisted search metadata only. It cannot
currently supply raw protocol bytes, certificate content or evidence selectors.
Design deliberate bounded inspection contracts; do not leak private source envelopes
or arbitrary filesystem/blob access. Use reviewed source/endpoint-bound reads that
recheck actual expiry and persistent suppression under the existing storage lock.
Preserve whole-observation removal and immutable original evidence; any sanitized
preview is separate from canonical source truth. Define explicit preview limits,
truncation, redaction and unsupported-format behavior before exposing fields.

Never render captured HTML, execute scripts, embed images/media, activate captured
URLs, follow redirects, decode compressed payloads without reviewed strict limits,
or resolve names/fetch AIA, OCSP, CRLs, certificate links or resources. Treat every
peer field and provenance URL as hostile. Make controls/bidi visible. Avoid exposing
cookies, authorization material, secrets or sensitive headers in previews/logs.
Synthetic-only access remains mandatory; this phase does not authorize real inputs
or claim comprehensive automated sensitive-content sanitization.

Certificate inspection must preserve verification=not_performed and distinguish
parsed assertions, parse failures, truncation and cryptographic validation. Do not
imply trusted identity, safe software or a vulnerability from exposure. Confidence
asserted/corroborated is ordinal, not calibrated probability. Preserve ambiguous
products/categories, source UUID/digest, rule/pack/engine/taxonomy identity and exact
bounded trace linkage. Negative/empty attempts must not erase earlier evidence or
silently combine metadata from different observations. Test hostile/malformed/large
fixtures, redaction, trace correctness and removal/expiry on every inspection route.

Current stored reads are POST /api/v1/search, /facets, /places and
/endpoints/{address}/{transport}/{port}/detail or /history. JSON requires explicit
schema_version:1, query and optional cursor; Content-Type application/json and
X-NetAtlas-Read:1. The header is a browser guard, not authentication. Preserve literal
loopback socket peers, approved local Host/Origin, same-origin Vite proxy, disabled
forwarded trust/access logs, no CORS/credentials and no public proxying. /healthz is
process liveness, not storage readiness. The static example is explicitly synthetic.

Use web/src/api/client.ts and generated schema.ts. After deliberate HTTP changes,
run `uv run --locked python -m netatlas.read_api.contract`; make check rejects drift.
Types are compile-time contracts, not runtime response validation. Preserve AbortSignal,
same-origin paths, omitted credentials, redirect refusal and generic errors. Never
log full queries, raw captures, credentials or exception bodies. No UI request may
start measurement, DNS, ingestion, downloads or derivation execution.

HTTP currently limits JSON to 16 KiB/depth 32/five-second body deadline, text/name to
256 characters, pages to 1–200, facets to 1–50 buckets, cursors to 2048 characters and
responses to four MiB. There is one in-flight data read, five-second SQL timeout and
ten-second shared-lock wait. Coordinate new inspection calls with the shared browser
read lane. An aborted browser fetch can leave server work finishing; 429 requires
explicit retry. Handle unavailable storage, output limits and invalid/expired cursors.

Search/history cursors bind the original query and route, use finish/start/UUID
keysets, expire after 15 nonrenewing minutes, depend on a process-local signing key
and stop after 10,000 hits. Resubmit the ORIGINAL query with next_cursor, never the
expanded response selection. Pages are live retained-data views, not snapshots.
The measurement/freshness cutoff is pinned, but actual retention and implicit-current
dataset validity are rechecked each page. Historical as_of cannot revive removed data.

Current attempt/open/evidence is selected BEFORE filters, with no older-match fallback.
History selects retained sources. Core is the default exact pack; enrichment requires
an explicitly selected dataset hash. Never choose an arbitrary newest dataset or mix
sources/derivations. Product text is simple-token AND over labels, not raw evidence.
Exact counts distinguish endpoint keys, source observations and all selected candidates.
Facets deduplicate per source/endpoint, include their own filter and report truncation;
history/multiple values may exceed totals. These are not physical devices or prevalence.

Preserve the Phase 8 geographic explorer: exact place search/disambiguation, category/
network/freshness/source filters, uncertainty/provenance, accessible list and page-only
MapLibre observation clusters. No whole-database map aggregate is implemented. Place
names are not identities: preserve stable ID, kind, admin and origin. Country selection
uses dataset country association; region boundary matching is explicit. Gazetteer
entries are not observation counts; datasets need a live unsuppressed associated source.
Stale/future place queries show provenance/state without places. Full boundaries are
not exported. Radius/box/boundary predicates test representative points, not uncertainty
disks. Missing radius is unknown, never zero; geography never precisely locates a device.

The UI uses one cancellable request lane plus generation guards. It holds one page,
replaces it on continuation, and clears results, places, selected-place metadata and
map points on hidden/pagehide or 60-second display expiry. It has no persistent or
back-page cache and no instant push-removal notification. Extend these protections
to inspection. Metadata is inert text; control characters become visible code points.
No arbitrary metadata links or external tiles, fonts, glyphs or geocoder requests.
The locally bundled module worker is required for Vite development and production.

The offline basemap covers Fiji only. Two tiny reviewed Natural Earth v5.1.2 Suva/Fiji
assets are intentionally committed with hashes/licenses in MAP_ASSETS; global files
and generated datasets remain ignored. Fictional documentation-IP/ASN associations
and same-name places/region are authored fixtures, not Natural Earth location claims.
`make demo` explicitly runs normal expiry maintenance and appends 13 sources for 12
endpoints through the real pipeline, printing a fresh dataset hash. It does not reset
owner data; repeating adds history. Demo dataset validity is seed time minus one day
through plus seven days. No automatic seed/download/refresh, paid service or global
geolocation/routing coverage exists. Preserve attribution and actual uncertainty.

Storage preserves immutable original v1/v2 sources in private raw blobs and
hash-placeholder JSONB/evidence_refs. UUID plus canonical digest distinguishes replay
from conflict. Fsynced blobs precede synchronous row commits; acknowledgement follows
commit. One advisory lock coordinates reads, writes, maintenance, GC and backup.
Independent attempt/open/evidence pointers order by finish/start/UUID. Derivations
are separately replayable; transactional outbox and same-DB receipts preserve replay.
Migration 0004 indexes authoritative rows directly; deletion has no asynchronous lag.

Sources expire after 30 days. Reads reject expiry; explicit maintenance removes
history, derivations, projections and unused snapshots/blobs. Persistent CIDR
suppression blocks ingestion and removes matching records. Tombstones/removal events
last 90 days. Spools, downloads, offline outputs and backups need separate removal.
Backups have a seven-day policy; old restores need current suppressions before use.
Never delete existing volumes/secrets to restart. No production role isolation,
encrypted backup, distributed workers, release or tag is implemented.

Discovery remains disabled/dry-run by default; enabled identity plus --measure is
required, and protocol collection additionally needs measurement.protocol_evidence.
Only literal IPs/small CIDRs, pinned policy, exclusions and shared budgets are allowed;
lab mode permits literal 127.0.0.1/::1 only. At most two connections, two GET / requests
and one TLS handshake per endpoint. No DNS/SNI, cookies, authentication, mail, STARTTLS,
crawling or device commands. Never add credential guessing, bypass, exploitation,
persistence or remote modification. Use synthetic/loopback fixtures, never Internet
sweeps as smoke tests.

Runtime pins remain Python 3.14.7, uv 0.12.19, Node 26.8.1 and npm 11.19.0. Inspect
Docker/Compose and the dedicated Colima netatlas profile before restarting anything.
Run `make db-up COMPOSE=docker-compose` and `make db-migrate`; Compose-plugin hosts
omit the override. Preserve the native arm64/amd64 PostGIS image, volume and secret.
TLS tests use OpenSSL and ephemeral keys. Browser setup requires
`npm --prefix web exec -- playwright install chromium`; CI uses --with-deps.
Full `make check-db COMPOSE=docker-compose` passed Phase 8 with 284 Python tests,
22 web unit/component tests and four production Chromium tests, strict checks,
OpenAPI drift, both builds, CLI smoke and database migration/backup/restore tests.
Verify current results. Browser tests create/drop a disposable netatlas_test_web_*
database and temporary blobs; ports 8000 and 5173 must be free. Desktop/mobile Axe
passed and screenshots were inspected; no comprehensive assistive-technology audit
is claimed. The ~1.29 MB main JS/511 kB worker build warning is documented.

At completion run meaningful inspection, hostile-content, redaction, accessibility
and end-to-end checks plus the full make check-db. Review tracked files/diff for
secrets, captures, datasets and generated outputs. Update authoritative docs with
actual results/limits and replace NEXT_PHASE with a complete Phase 10 kickoff.
Commit with a Phase 9 message, push if a remote exists, verify local HEAD equals
remote delivery HEAD and a clean tree, inspect CI, report checks/commit/push/blockers/
current state and the full Phase 10 kickoff, then stop. No release/tag. Ask only for
genuine blockers, credentials, permissions or unavoidable manual actions after all
independent authorized work is complete.
