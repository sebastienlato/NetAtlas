# PHASE 12 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global Internet
Exposure Search & Visualization, an independent university thesis project. Complete
exactly **Phase 12 — Operational hardening** in this fresh Work chat. Do not begin
Phase 13. Repository files are authoritative; respect owner changes and make routine
engineering decisions autonomously. Ask only for genuine blockers after completing
independent authorized work. No release or tag.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md and SECURITY.md, then docs/SCHEDULING.md, DISTRIBUTED.md, STORAGE.md,
API.md, DATA_MODEL.md, DISCOVERY.md, PROTOCOL_EVIDENCE.md, FINGERPRINTS.md, ENRICHMENT.md,
SEARCH.md, SEARCH_BENCHMARK.md, GEOGRAPHIC_UI.md, MAP_ASSETS.md and INSPECTION.md.
Inspect Git status/remotes, actual runtime/Compose state, control/worker/scheduler,
transaction/outbox/restore behavior, read/browser contracts and acceptance tests before
designing. Do not rely on prior chat history or represent future modules as implemented.

**Current delivery:** package 0.12.0; schedule input/plan 1, coverage-refresh-1 and
explicit-authored-seeds-only-1; control envelope 1; HTTP/local query 1; preview policy
synthetic-preview-1; Settings 3; observation/manifest 2 with explicit v1 reads;
fingerprint pack/result 1, engine fingerprints-1, taxonomy netatlas-categories-1;
enrichment bundle/result 1, engine enrichment-1; Alembic head 0006. Python/FastAPI/
Pydantic, PostgreSQL 18.3/PostGIS 3.6.4, SQLAlchemy/psycopg, cryptography 48.0.1 and
React/TypeScript/Vite/MapLibre 6.12.0 are implemented. OpenSearch remains deferred by
the small synthetic benchmark. No real ingestion, Internet campaign, public deployment,
worldwide worker network, production role isolation or encrypted backup exists.

Implement proportionate structured telemetry, operational dashboards/readiness,
bounded resource handling, secrets/access control, reproducible local deployment and
a retention/restore runbook. Acceptance is a controlled authored-synthetic/loopback
load and failure exercise, verified backup/restore, authenticated control plane,
opt-out handling, dependency review and local deployment smoke test. Preserve exact
measurement/source/count semantics. Define liveness versus dependency readiness and
failure/degraded states honestly; avoid leaking endpoint addresses, queries, peer data,
operator contacts, secrets or raw exception details through metrics/logs/dashboards.
Make least-privilege/process/credential changes deliberate, recoverable and tested.
Inspect existing state before any rotation or deployment change; do not reset owner
volumes, passwords, data or worker boot identities. Do not infer authorization for paid
infrastructure, public listeners, live datasets, real targets or a worldwide campaign.
No Phase 13 benchmark/evaluation campaign or Phase 14 release work.

Preserve Phase 11 scheduling. Pure offline planning uses only bounded authored
routed/unrouted/unknown documentation/loopback regions, explicit sourced IPv6 seeds,
canonical universe/policy/config/seed/input identities, SHA-ranked sampling, /24-/48
round-robin order and explicit round rotation. Logical shards partition one global
plan and confer no worker authority or independent budget. Fairness is dispatch order,
not successful coverage or latency; changing eligible sets can bias results. IPv6
coverage denominators are seeds/regions, never exhaustive address space. Counts
separate excluded/blocked/fresh/eligible/sampled-out/deferred/scheduled candidates from
admitted/measured/incomplete/retained/refreshed sources, never devices or prevalence.

A refresh is a new explicitly scheduled measurement bound to the exact latest retained
attempt UUID/digest, including negative/empty history; default cooldowns are open one
day, closed seven days, timeout/error two days. New job/attempt/source identities and
ordinary traffic budgets apply. Delivery replay is never a refresh. Admission rechecks
actual source history, suppressions, unresolved issued attempts, expiry and queue limits
under the existing DB lock. Exact schedule replay returns its original campaign, even
a cancelled/restored one. Issued attempts without receipts remain blocked for retained
control history; pruning that history is explicit, not automatic retry. Plans expire
within 1–3600 seconds and universe validity; future DB-clock plans fail closed. No
unattended scheduling or expiry daemon currently exists. UDP remains explicitly deferred
without a qualified protocol-specific request/response/amplification budget and corpus.

Keep offline planning separate from executable lab scope. Execution requires enabled
operator identity, explicit lab_loopback, --synthetic and --measure, and accepts only
literal 127.0.0.1/::1 endpoints, at most 16 ports/32 jobs. No documentation-to-loopback
translation. Standalone discovery stays disabled/dry-run by default, literal/small-CIDR
bounded, with pinned policy and deny-first exclusions/opt-outs. Protocol capture also
requires measurement.protocol_evidence. No credential guessing, authentication bypass,
exploitation, persistence, remote modification, destructive actions, DNS/SNI, cookies,
authentication, mail, STARTTLS, crawling, streams, device commands or traffic-amplifying
retries. At most two connections, two GET / requests and one TLS handshake per endpoint.

Preserve worker authority. Two local processes authenticate to a separate loopback
coordinator using generated private per-worker bearer credentials; workers get no DB
secret. Tokens never enter Settings hashes, logs, fixtures or Git. Registration binds
stable worker UUID, increasing persisted boot generation and session UUID; reordered
registration cannot restore old authority. Jobs bind attempt/reserved observation UUID,
increasing fence, lease/hard horizon and delivery session. Only unstarted leases can
reassign, at most three times. Once any permit is issued, loss becomes uncertain and
never automatically remeasures. Original saved results may recover delivery-only
authority within 24 hours; cancelled/suppressed/reassigned work cannot regain authority.

Every connection, including TLS/second connections, needs a durable one-use central
permit valid 250 ms conservatively from worker monotonic request start. Reservations
cover that window plus global/per-prefix spacing. Slow/lost grants burn; wait replies
consume none. Changed rates respect prior admission/new interval; clock regression
fails closed. At most min(2, configured concurrency) sockets; uncertain/cancelled issued
attempts keep possible slots until fixed hard horizons. Restart retains pacing/fencing.
One-second heartbeats renew ten-second leases; control failure normally closes active
sockets within about three seconds, subject to scheduling. Issued grants/in-flight
connections prevent instantaneous physical fencing. Workers remain cooperative trusted
code, not a hostile-worker sandbox.

One fsynced pending slot and at most one stage per worker, each ≤1 MiB; complete result
saved before delivery. Five bounded-backoff delivery attempts resend identical UUID/
digest. Storage failure keeps the slot and blocks claims; new boots reconcile before
work. Keep boot.json and credentials. One active campaign, 128 pending/1024 retained
jobs, two worker identities; do not silently relax bounds. Control HTTP: 1-MiB delivery,
16-KiB other bodies, depth 32, five-second body deadline, eight in-flight requests,
no Origin/Cookie/CORS/forwarded trust/access logs. Separate 1-MiB schedule metadata does
not enlarge the 12-KiB worker campaign snapshot. Read API/UI has no measurement controls.

Global stop durably cancels all work and blocks admission/delivery; allow-new-work only
reopens new admission. It never revives jobs, clears suppressions or resets authority.
Suppression/source removal and matching job revocation commit together. A DB outage
may prevent committing stop: terminate workers locally; heartbeat failure still stops
cooperative I/O. Offline worker copies cannot receive deletion. Independently remove/
quarantine worker pending copies, standalone spools, schedule files, outputs and backups.

Keep collectors, domain, derivations, scheduler, worker control, storage/search, API and
UI separable. Immutable original v1/v2 sources live in private raw blobs plus hash-
placeholder JSONB/evidence_refs. UUID and canonical digest distinguish replay/conflict.
Fsynced blobs precede synchronous commit; acknowledge afterward. Source/projection/
outbox/job receipt share one transaction under the existing advisory lock. Coordinate
readers, writes, GC, maintenance and backups. Never edit shipped migrations. External
outbox effects remain unimplemented; same-DB receipts do not imply arbitrary external
exactly-once delivery. Latest attempt/open/evidence independently order finish/start/UUID;
negative/empty results preserve older evidence. Derivations stay replayable; direct
indexes have no asynchronous deletion-copy lag.

Sources expire after 30 days; actual reads reject expiry before maintenance. Whole-
observation removal preserves immutable truth; no rewritten sanitization claims.
Tombstones/removal events and control metadata, including schedule/source summaries,
retain 90 days; backups seven days. Restore only into a separate empty DB, migrate,
cancel all historical campaigns/jobs, expire leases and set global stop. Keep it offline
until full verification and current suppression reapplication; explicit reopening
follows that review. Do not reset owner state to make a restore or test pass.

Preserve Phase 9 exact endpoint/source UUID/digest/optional source-bound derivation
inspection. Wrong/missing/expired/suppressed identities yield generic 404. Verify source
hashes and trace pointers/ranges/slices under the lock with before/after retention checks.
No arbitrary blob/path/raw download, source export or request-triggered derivation.
synthetic-preview-1 permits reviewed inert UTF-8 only: 2048 original bytes body/greeting,
256 per scalar, visible controls/bidi, allowlisted HTTP fields, no unreviewed headers/
SSH comments or raw/hex/base64 fallback. Recognized sensitive markers withhold whole
candidates before truncation; this is not comprehensive sanitization or real-input
permission. Captured URLs/HTML never execute or become resources. Certificate DER
exports bounded unverified assertions only, no extensions/trust claims/network fetches.
Preserve all ambiguous fingerprint candidates and exact rule/pack/engine/source trace.

Preserve read API schema 1: JSON Content-Type, X-NetAtlas-Read:1 non-secret guard,
literal-loopback peer/approved Host/Origin, no CORS/credentials/forwarded trust/access
logs and same-origin proxy. /healthz currently means liveness; add readiness separately.
Use generated schema.ts/client.ts, regenerate with `uv run --locked python -m
netatlas.read_api.contract` after intentional HTTP changes; preserve AbortSignal,
omitted credentials, redirect refusal and generic errors. Bounds: 16-KiB JSON/depth32,
five-second body deadline, 256-character text, 1–200 rows, 1–50 facets, 2048-character
cursors, four-MiB responses, one in-flight read, five-second SQL/ten-second lock wait.
Query/route-bound finish/start/UUID cursors have nonrenewing 15-minute life and 10000
traversal cap. Pages are live retained views; historical as_of cannot revive removal.

Source choice precedes filters without older-match fallback. Core is default exact
pack; enrichment requires explicit dataset hash, no arbitrary newest/cross-source
metadata. Counts separate endpoints/sources/candidates. Geography is approximate
representative points with unknown radii and provenance, never precise device location.
UI retains one displayed page with a shared cancellable read lane/generation guards;
hidden/pagehide/60-second expiry clears map, places, selection, inspection and timeline.
No persistent cache, push deletion claim or captured resources. Timeline has 20 retained
attempts including negatives. Keep local map assets, inert rendering and post-React
focus. Existing approximately 1.30-MB JS/511-kB worker warning is documented.

Offline basemap covers Fiji only; tiny reviewed Natural Earth v5.1.2 assets retain
hashes/licenses in MAP_ASSETS. `make demo` expires old data then appends 13 authored
sources/12 endpoints, never resets owner state, and prints a fresh dataset hash valid
seed time minus one day through plus seven days. No automatic download/seed/refresh.

Runtime pins: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0. Inspect Docker/Compose
and dedicated Colima netatlas before restarting. Run `make db-up COMPOSE=docker-compose`
and `make db-migrate`; Compose-plugin hosts omit the override. Preserve native arm64/
amd64 PostGIS, volume and secret. TLS tests generate ephemeral OpenSSL keys. Browser
setup: `npm --prefix web exec -- playwright install chromium` (CI adds --with-deps).
Ports 8000/5173 must be free; browser tests use disposable netatlas_test_web_* DBs and
temporary blobs. Worker tests use random loopback ports/generated credentials.

Phase 11 full make check-db passed **374 Python tests, 26 web tests and five production
Chromium tests**, including 25 scheduling cases and scheduled two-process HTTP/TLS with
lost ACKs/no extra probes. Existing kill/restart/fencing/leases/budgets/retention/upgrade/
restore/browser acceptance passes. Git/Actions and the previous completion report give
actual delivery status. No worldwide capacity or real-world accuracy is qualified.

At completion, run meaningful operational/load/failure/retention/restore/access tests
and full `make check-db`. Review tracked files/diff for secrets, captures, outputs and
datasets. Update authoritative docs and replace NEXT_PHASE with a complete Phase 13
kickoff. Commit with a Phase 12 message, push if a remote exists, verify local HEAD
equals remote delivery HEAD and a clean tree, inspect CI, report results/commit/push/
blockers/current state and the full Phase 13 kickoff, then stop. No release/tag and no
Phase 13 implementation. Ask only for genuine blockers or unavoidable owner actions.
