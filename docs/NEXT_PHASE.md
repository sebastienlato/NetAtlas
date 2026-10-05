# PHASE 11 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global Internet
Exposure Search & Visualization, an independent university thesis project. Complete
exactly **Phase 11 — Coverage and refresh scheduling** in this fresh Work chat. Do not
begin Phase 12. Repository files, not prior chat history, are authoritative. Make routine
engineering decisions autonomously; ask only for genuine blockers after independent
authorized work. Respect owner changes. No release or tag.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md, SECURITY.md and docs/DISTRIBUTED.md, API.md, DATA_MODEL.md, STORAGE.md,
DISCOVERY.md, PROTOCOL_EVIDENCE.md, FINGERPRINTS.md, ENRICHMENT.md, SEARCH.md,
SEARCH_BENCHMARK.md, GEOGRAPHIC_UI.md, MAP_ASSETS.md and INSPECTION.md first. Inspect
Git status/remotes, runtime/Compose state, worker/control/collector code, transaction/
outbox/restore behavior, read API/browser contracts and acceptance tests before designing.

Phase 10 delivered package **0.11.0**, control envelope **1**, HTTP/local query schemas
**1**, preview policy **synthetic-preview-1**, config **3**, observation/manifest **2**
with explicit v1 reads; fingerprint pack/result **1**, engine fingerprints-1, taxonomy
netatlas-categories-1; enrichment bundle/result **1**, engine enrichment-1; Alembic head
**0005**. Python/FastAPI/Pydantic, PostgreSQL 18.3/PostGIS 3.6.4, SQLAlchemy/psycopg,
cryptography 48.0.1 and React/TypeScript/Vite/MapLibre 6.12.0 are implemented. OpenSearch
remains deferred by the small synthetic benchmark. No real ingestion, Internet campaign,
public deployment, worldwide worker network, production role isolation or encrypted
backup exists.

Implement reproducible routed-space sampling/sharding, an explicit IPv6 seed policy,
prefix fairness, stale-service refresh priorities, opt-out propagation and stop controls.
Acceptance uses a **small authored synthetic address universe** to demonstrate coverage,
schedule determinism, expiration and shared global budgets. Evaluate one bounded UDP
collector only if its protocol budget and fixture evidence fit this phase; otherwise
explicitly defer it. Do not infer authorization for live routing/geography downloads,
real targets or an Internet campaign. Keep offline schedule planning separate from the
existing narrower literal-loopback execution adapter. Do not implement Phase 12 telemetry,
public deployment or production access-hardening as incidental scope.

Define coverage denominators, exclusions, unknown/unrouted areas, seed/source provenance,
versioned policy/config/seed identities and deterministic ordering. Distinguish scheduled,
admitted, measured, incomplete/uncertain, retained and refreshed sources; these are not
devices, worldwide completeness or prevalence. Refresh is an explicit new scheduled
measurement with its own identity and budget, never a delivery retry. Preserve original
attempt/source identities and negative/empty history semantics. Define fairness and
expiration under bounded queues, cancellation, coordinator failure, changing exclusions
and unavailable storage. Test those behaviors against independent authored truth.

Preserve Phase 10 worker authority. Two local processes authenticate to a separate
loopback coordinator using generated private per-worker bearer credentials; workers do
not get DB credentials. Tokens never enter Settings hashes, logs, fixtures or Git. The
read API/UI has no measurement controls and remains separate. Registration uses stable
worker UUID, persisted increasing boot generation and session UUID; older/reordered
registration cannot restore authority. Jobs have attempt UUID, reserved observation UUID,
increasing fence, lease/hard horizon and delivery session. Only unstarted leases can be
reassigned, at most three assignments. Once any connection permit is issued, failure
becomes uncertain and **never automatically remeasures**. Saved original results can
recover delivery-only authority within 24 hours of claim; stale/reassigned/cancelled/
suppressed work cannot regain measurement authority.

Every target connection, including TLS/second connections, requires a durable one-use
central permit. Its 250-ms validity is conservatively measured from the worker's monotonic
request start; DB reservations cover that window plus global and per-prefix spacing.
Slow/lost grants are burned. A wait reply consumes no grant. Changed rates respect the
prior admission and new interval; clock regression fails closed. At most min(2, configured
concurrency) sockets are admitted; uncertain/cancelled issued attempts retain their possible
socket slots until their fixed hard horizon. Coordinator restart retains pacing/authority.
Heartbeats renew 10-second leases once per second; control failure cancels active sockets,
normally within about three seconds subject to scheduling. Already-issued grants/in-flight
connections prevent any claim of instantaneous physical fencing. Authenticated workers
are cooperative trusted code, not a hostile-worker sandbox.

Workers keep one fsynced pending slot and at most one staging copy, each at most 1 MiB.
A complete observation is saved before delivery. Five delivery attempts with bounded
backoff resend the identical UUID/digest; an unavailable backend leaves the slot and
blocks claims. A new boot drains/reconciles the slot before any work. Keep boot.json and
credentials on restart; never reset their identity to resolve a failure. Current explicit
queue bounds are 128 pending/1024 retained jobs, one active campaign, at most 32 literal-
loopback endpoints, three assignments/job, and two provisioned worker identities. Scheduling
changes to these bounds/semantics must be deliberate, documented and tested, not silently
relaxed. Control HTTP has 1-MiB delivery/16-KiB other bodies, depth 32, five-second body
deadline, eight in-flight requests, no Origin/Cookie/CORS/forwarded trust/access logs.

Never add credential guessing, authentication bypass, exploitation, persistence, remote
modification or destructive actions. Measurement remains bounded normal unauthenticated
interaction. Default development/tests to authored synthetic or literal-loopback fixtures;
no Internet sweeps or real ingestion are authorized. Discovery stays disabled and dry-run
by default, requiring enabled operator identity and --measure. Distributed enqueue also
requires --synthetic and literal-loopback lab scope. Protocol capture additionally requires
measurement.protocol_evidence. Preserve literal IP/small CIDR bounds, pinned policy,
exclusions/opt-outs and lab mode restricted to literal 127.0.0.1/::1. At most two connections,
two GET / requests and one TLS handshake per endpoint. No DNS/SNI, cookies, authentication,
mail, STARTTLS, crawling, streams, device commands or traffic-amplifying retries.

Keep collectors, domain, derivations, scheduler, worker control, storage/search, API and
UI separable. Storage preserves immutable v1/v2 sources in private raw blobs and hash-
placeholder JSONB/evidence_refs. UUID plus canonical digest separates replay from conflict.
Fsynced blobs precede synchronous row commit; acknowledge only after commit. Worker
source/projection/outbox and job receipt commit in the **same transaction** under the
existing advisory lock. Keep readers, writes, GC, maintenance and backup coordinated.
Never edit shipped migrations; add reviewed revisions. External outbox effects remain
unimplemented; same-DB receipts do not imply arbitrary external exactly-once delivery.
Latest attempt/open/nonempty-evidence pointers independently order by finish/start/UUID;
negative/empty observations do not erase older evidence. Derivations remain replayable.
Migration 0004 indexes authoritative rows directly; deletion has no search-copy lag.

Sources expire after 30 days; actual-time reads reject expiry before maintenance. Persistent
CIDR suppression blocks ingestion and revokes worker admission/delivery. Whole-observation
removal preserves immutable truth; never rewrite evidence to claim original sanitization.
Tombstones/removal events and explicit control metadata retention last 90 days; backups
have a seven-day policy. Worker copies, standalone spools, outputs, datasets and backups
need independent deletion/quarantine. Offline workers cannot receive deletion. Restore
into a separate empty DB cancels every historical control job/campaign and expires leases;
keep that destination offline until full restore and current suppression reapplication
succeed. Never reset owner volumes, secrets or existing data to restart.

Preserve Phase 9 inspection: exact endpoint/observation UUID/source digest and optional
exact source-bound derivation ID. Wrong/missing/expired/suppressed identities give generic
404. Reconstruct under the lock, check retention before/after projection, verify canonical
source hashes and trace pointer/range/slice hashes. No arbitrary blob/path read, source
export, raw download or derivation execution from a request. Pure inspection stays separate
from canonical evidence. synthetic-preview-1 permits only reviewed inert UTF-8 fields:
2,048 original bytes for body/greeting, 256 per scalar, visible controls/bidi. Allowlisted
HTTP version/status/Server/Content-Type/Content-Length; other headers and SSH comments/
preambles withheld. Unsupported/encoded/binary/malformed content has no raw/hex/base64
fallback. Recognized sensitive markers withhold the entire candidate before truncation;
this is not comprehensive sanitization or real-input authorization. Captured URLs/HTML
remain inert, never links/resources/scripts/media. Certificate DER exposes bounded
assertions only with verification=not_performed, explicit parsing/truncation states,
no identity/trust/vulnerability claim, extensions or network fetching. Preserve all
ambiguous fingerprint candidates and exact rule/pack/engine/taxonomy/source identities;
asserted/corroborated confidence is ordinal, trace excerpts withheld.

Preserve read API schema 1: JSON Content-Type and non-secret X-NetAtlas-Read:1, literal-
loopback peer/approved Host/Origin, no CORS/credentials/forwarded trust/access logs and
same-origin Vite proxy. /healthz is liveness, not readiness. Use generated schema.ts and
client.ts; regenerate with `uv run --locked python -m netatlas.read_api.contract` after
intentional HTTP changes. Keep AbortSignal, omitted credentials, redirect refusal and
generic errors. UI reads cannot measure, ingest, download, resolve or derive. Limits:
16-KiB JSON/depth 32/five-second body deadline, 256-character text/name, 1–200 rows,
1–50 facet buckets, 2,048-character cursors, four-MiB responses, one in-flight read,
five-second SQL and ten-second shared-lock wait. Cursors bind original query/route,
finish/start/UUID keysets, nonrenewing 15-minute lifetime and process-local signing key;
traversal stops at 10,000. Pages are live retained views, not snapshots. Actual retention
and implicit-current dataset validity are rechecked; historical as_of cannot revive removal.

Current source choice precedes filters, with no older-match fallback. Core is the default
exact pack; enrichment requires an explicit dataset hash, never arbitrary newest versions
or cross-source metadata. Counts distinguish endpoints/sources/all candidates; facets
deduplicate per source/endpoint and report truncation. Geography uses approximate
representative points, explicit unknown radius, stable place IDs/admin/kind/origin and
attribution. Country association differs from boundary matching. No precise device location
or whole-database map aggregate is claimed. The UI shares one cancellable read lane with
generation guards and original-query continuation. One displayed page/view; hidden/pagehide
or 60-second expiry clears results/places/map/selection/inspection/timeline. No persistent
cache or push deletion notification. Timeline pages have 20 retained attempts, including
negative/empty ones. Keep inert rendering, focus after React commits and locally bundled
map resources. Existing roughly 1.30-MB JS / 511-kB worker warning is documented.

The offline basemap covers Fiji only. Tiny reviewed Natural Earth v5.1.2 assets retain
hashes/licenses in MAP_ASSETS; global/generated data stays ignored. `make demo` explicitly
expires old data then appends 13 authored sources for 12 endpoints, prints a fresh dataset
hash and never resets owner data. Demo validity is seed time minus one day through plus
seven days. No automatic seed, download, refresh, paid service or real routing/geo coverage.

Runtime pins: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0. Inspect Docker/Compose
and the dedicated Colima netatlas profile before restarting. Run `make db-up
COMPOSE=docker-compose` and `make db-migrate` (Compose-plugin hosts omit the override).
Preserve native arm64/amd64 PostGIS, volume and secret. TLS tests generate ephemeral keys
using OpenSSL. Browser setup: `npm --prefix web exec -- playwright install chromium`
(CI adds --with-deps). Ports 8000 and 5173 must be free for production browser tests;
they use a disposable netatlas_test_web_* DB and temporary blobs. Worker tests use random
loopback ports, generated credentials and isolated databases.

Phase 10 full make check-db passed with **348 Python tests, 26 web tests and five
production Chromium tests**; final delivery status is in Git/Actions. The
worker suite includes real two-process HTTP/TLS capture, lost delivery ACKs, kill/restart,
no extra probes, authentication/fencing/leases/budgets, storage backpressure, cancellation,
retention, populated migration and backup/restore quarantine. Full make check-db also
preserves the earlier Python, web and production Chromium acceptance. No worldwide capacity,
real-world accuracy or comprehensive assistive-technology qualification is claimed.

At completion run meaningful scheduling/coverage/fairness/IPv6/refresh/opt-out/stop/failure
acceptance and full `make check-db`. Review tracked files/diff for secrets, captures,
outputs and datasets. Update authoritative docs with actual behavior/results/limits and
replace NEXT_PHASE with a complete Phase 12 kickoff. Commit with a Phase 11 message,
push if a remote exists, verify local HEAD equals remote delivery HEAD and a clean tree,
inspect CI, report checks/commit/push/blockers/current state and the full Phase 12 kickoff,
then stop. No release/tag and no Phase 12 implementation. Ask the owner only for genuine
blockers, credentials, permissions or unavoidable manual actions after independent work.
