# PHASE 10 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global Internet
Exposure Search & Visualization, an independent university thesis project. Complete
exactly **Phase 10 — Distributed measurement** in this fresh Work chat. Do not begin
Phase 11. Repository files, not prior chat history, are authoritative. Make routine
engineering decisions autonomously; ask only for genuine blockers after finishing
independent authorized work. Respect owner changes. No release or tag.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md, SECURITY.md and docs/API.md, DATA_MODEL.md, STORAGE.md, DISCOVERY.md,
PROTOCOL_EVIDENCE.md, FINGERPRINTS.md, ENRICHMENT.md, SEARCH.md, SEARCH_BENCHMARK.md,
GEOGRAPHIC_UI.md, MAP_ASSETS.md and INSPECTION.md first. Inspect Git status/remotes,
toolchains, existing discovery/budget/collector code, storage transactions/outbox,
read API, browser client and tests before designing the new control plane.

Phase 9 delivered package **0.10.0**, HTTP/local query schemas **1**, preview policy
**synthetic-preview-1**, config **3**, observation/manifest **2** with explicit v1
reads; fingerprint pack/result **1**, engine fingerprints-1, taxonomy
netatlas-categories-1; enrichment bundle/result **1**, engine enrichment-1; Alembic
head **0004**. Python 3.14/FastAPI/Pydantic, PostgreSQL 18.3/PostGIS 3.6.4,
SQLAlchemy/psycopg, cryptography 48.0.1 and React/TypeScript/Vite/MapLibre 6.12.0
are implemented. No distributed workers, real-data ingestion, Internet campaign,
public deployment, production role isolation or encrypted backup exists.
OpenSearch is deferred by the small local synthetic benchmark.

Implement two local/containerized workers, authenticated registration, durable
leases/heartbeats, ingestion backpressure and retry/idempotency. Acceptance includes
worker failure/restart and duplicate delivery drills, centrally budgeted rates and
no paid infrastructure or real global campaign. Keep control-plane authentication
separate from the unauthenticated trusted-local read API. Do not extend UI reads
into measurement controls or expose them publicly. Use generated ignored local
credentials; never log/store secrets in configuration hashes, fixtures or Git.

Design explicit worker/job/attempt identities and versioned bounded envelopes;
lease ownership, expiry, fencing, restart/reclaim and late-result semantics; durable
acknowledgement and bounded queue/spool/backpressure behavior. Delivery retries must
not silently become extra target measurements. Preserve original observation UUIDs
and digests across replay, reject identity conflicts and stale authority, and test
lost acknowledgements, duplicate/reordered delivery, cancellation, worker death,
coordinator restart and storage unavailability. Central admission must prevent
workers multiplying global/per-prefix connection budgets, including TLS/second
connections. Define safe behavior when coordination or heartbeats are unavailable.
Use reviewed migrations; never edit shipped migrations. Do not build Phase 11 routed
space sampling, coverage/refresh scheduling, UDP probing or global distribution.

Never add credential guessing, authentication bypass, exploitation, persistence or
remote modification. Measurement remains bounded normal unauthenticated interaction.
Default all development/tests to authored synthetic or literal-loopback fixtures.
No Internet sweeps or real ingestion are authorized. Discovery stays disabled and
dry-run by default, requiring enabled operator identity plus --measure; protocol
capture additionally requires measurement.protocol_evidence. Preserve literal IP/
small CIDR scopes, pinned policy, exclusions/opt-outs, shared budgets and lab mode
limited to literal 127.0.0.1/::1. At most two connections, two GET / requests and one
TLS handshake per endpoint. No DNS/SNI, cookies, authentication, mail, STARTTLS,
crawling, streams, device commands or retries that amplify traffic.

Keep collectors, domain, derivations, storage/search, API, worker control plane and
UI separable. Storage preserves immutable v1/v2 sources in private raw blobs and
hash-placeholder JSONB/evidence_refs. UUID plus canonical digest separates replay
from conflict. Fsynced blobs precede synchronous row commits; acknowledge only after
commit. One advisory lock currently coordinates reads, writes, GC, maintenance and
backup. Any distributed adaptation must retain these guarantees and have tested
failure behavior. Independent latest attempt/open/nonempty-evidence pointers order
by finish/start/UUID. Negative/empty attempts never erase older evidence. Derivations
are independently replayable; transactional outbox and same-DB receipts preserve
local replay. External delivery guarantees must be explicitly designed and tested.
Migration 0004 indexes authoritative rows directly; deletion has no search lag.

Sources expire after 30 days; actual-time reads reject expiry even before maintenance.
Persistent CIDR suppression blocks ingestion and removes matching records. Tombstones
and removal events last 90 days. Whole-observation removal preserves immutable truth;
never rewrite evidence to claim it was originally sanitized. Spools, downloads,
worker copies, outputs and backups need explicit independent deletion/quarantine.
Backups have a seven-day policy; old restores require current suppressions. Do not
delete existing volumes, secrets or owner data to restart. Opt-out/cancellation
propagation in workers must fail safely; full coverage scheduling remains Phase 11.

Preserve Phase 9 inspection: POST /api/v1/endpoints/{address}/{transport}/{port}/inspection
requires exact observation UUID/source digest and optional exact source-bound derivation
ID. Wrong endpoint/source/derivation or missing/expired/suppressed records return generic
404. Reconstruct under the storage lock, check retention before and after projection,
verify canonical hashes and trace pointer/range/slice hashes. No arbitrary blob/path
read, source envelope export, raw download or derivation execution from a request.
Pure inspection projections remain separate from canonical evidence.

synthetic-preview-1 allows only reviewed UTF-8 previews: body/greeting at most 2,048
original bytes and scalar fields at most 256, with visible controls/bidi. Allowlisted
HTTP version/status/Server/Content-Type/Content-Length; all other headers and SSH
comments/preambles withheld. Only supported unencoded text/plain or text/html bodies;
malformed, binary, JSON/media, duplicate/unreviewed types and encoded bodies have no
raw/hex/base64 fallback. Recognized sensitive markers redact the entire field/body
before truncation. This is not comprehensive sensitive-content sanitization and does
not authorize real input. Captured HTML/URLs are inert text, never executable or
resource links. No scripts, media, redirects, compression decoding or name resolution.

Certificate DER parsing exposes bounded subject/issuer/serial/time/algorithm assertions
only, preserving verification=not_performed. Parsed, parse-failed, unsupported,
source-truncated, chain-truncated and display-truncated states remain explicit.
No trusted identity, cryptographic validation, safe-software or vulnerability claim;
no extensions, AIA/OCSP/CRL/certificate-resource fetching. Confidence asserted/
corroborated is ordinal, not calibrated probability. Preserve every ambiguous
candidate and exact source/rule/pack/engine/taxonomy identity; trace excerpts are withheld.

Existing search/facets/places and endpoint detail/history remain metadata routes.
JSON requires schema_version:1, Content-Type:application/json and X-NetAtlas-Read:1.
The header is a browser guard, not authentication. Preserve literal-loopback socket
peers, approved local Host/Origin, disabled forwarded trust/access logs, no CORS or
credentials and same-origin Vite proxy. /healthz is process liveness, not readiness.
Use generated web/src/api/schema.ts and client.ts; regenerate via
`uv run --locked python -m netatlas.read_api.contract` after deliberate HTTP changes.
Types are compile-time contracts, not runtime validation. Preserve AbortSignal,
omitted credentials, redirect refusal and generic errors; never log queries/raw
captures/credentials/exception bodies. UI reads must not trigger measurements,
ingestion, downloads, DNS or derivations.

HTTP bounds remain 16-KiB JSON/depth 32/five-second body deadline, 256-character
text/name, 1–200 rows, 1–50 facet buckets, 2,048-character cursors, four-MiB responses,
one in-flight read, five-second SQL timeout and ten-second shared-lock wait.
Cursors bind original query/route, finish/start/UUID keysets, nonrenewing 15-minute
lifetime and process-local signing key; traversal ends at 10,000 hits. Resubmit the
original query, not expanded selection. Pages are live retained views, not snapshots;
actual retention and implicit-current dataset validity are rechecked every page.
Historical as_of cannot revive removed data.

Current attempt/open/evidence is selected before filters, with no older-match fallback.
Core is the default exact pack; enrichment requires an explicit dataset hash.
Never choose an arbitrary newest dataset or mix observation/derivation metadata.
Counts distinguish endpoint keys, sources and all candidates; facets deduplicate per
source/endpoint and report truncation. These are not devices or prevalence.
Geography uses approximate representative points and explicit unknown radius, stable
place IDs/admin/kind/origin and attribution. Country association and boundary matching
are distinct. No whole-database map aggregate or precise device location is claimed.

Preserve the geographic explorer and inspection/timeline shared cancellable read lane,
generation guards, original-query continuation and generic errors. One displayed
page/view; hidden/pagehide or 60-second expiry clears results/places/selection/map/
inspection/timeline. No persistent/back-page cache or push deletion notification.
Aborted requests can leave server work finishing; 429 uses explicit retry. Timeline
includes all retained attempts with 20-row pages. Inspection links one exact source.
Keyboard focus/skip link target the active view. Captured/provenance URLs remain
inert, controls visible, and all map resources/worker are bundled locally.

The offline basemap covers Fiji only. Tiny reviewed Natural Earth v5.1.2 Suva/Fiji
assets retain hashes/licenses in MAP_ASSETS; global/generated datasets stay ignored.
`make demo` explicitly runs expiry maintenance and appends 13 authored sources for
12 endpoints, prints a fresh dataset hash and never resets owner data. Demo validity
is seed time minus one day through plus seven days. No automatic seeding, download,
refresh, paid service or global routing/geography coverage exists.

Runtime pins: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0. Inspect Docker,
Compose and the dedicated Colima netatlas profile before restarting. Run
`make db-up COMPOSE=docker-compose` and `make db-migrate`; Compose-plugin hosts omit
the override. Preserve the native arm64/amd64 PostGIS image, volume and secret.
TLS tests use OpenSSL/ephemeral keys; inspection fixtures generate certificates in
memory. Browser setup: `npm --prefix web exec -- playwright install chromium`
(CI adds --with-deps). Ports 8000 and 5173 must be free for production browser tests.
They create/drop a disposable netatlas_test_web_* database and temporary blobs.

Phase 9 validation: full make check-db passed with **312 Python tests, 26 web
unit/component tests and five production Chromium tests**, strict checks, OpenAPI
drift, both builds, CLI smoke and migration/backup/restore acceptance. Hostile stored
content produced no active resources or external browser requests; desktop/mobile
Axe passed and screenshots were inspected. No comprehensive assistive-technology,
Internet-scale throughput or real-world accuracy qualification is claimed. The
roughly 1.30-MB main JS / 511-kB worker build warning remains documented.

At completion run meaningful worker/authentication/lease/budget/failure/restart/
duplicate/backpressure tests and full make check-db. Review tracked files/diff for
secrets, captures, generated outputs and datasets. Update authoritative docs with
actual behavior/results/limits and replace NEXT_PHASE with a complete Phase 11 kickoff.
Commit with a Phase 10 message, push if a remote exists, verify local HEAD equals
remote delivery HEAD and a clean tree, inspect CI, report checks/commit/push/blockers/
current state and the full Phase 11 kickoff, then stop. No release/tag and no Phase 11
implementation. Ask the owner only for genuine blockers, credentials, permissions
or unavoidable manual actions after all independent authorized work is done.
