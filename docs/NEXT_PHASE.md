# PHASE 13 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
Complete exactly **Phase 13 — Thesis evaluation** in this fresh Work chat. Do not
begin Phase 14, create a release or tag. Repository files are authoritative; respect
owner changes and make routine engineering decisions autonomously. Ask only for
genuine blockers after completing independent authorized work.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md and SECURITY.md, then docs/OPERATIONS.md, DEPENDENCIES.md, SCHEDULING.md,
DISTRIBUTED.md, STORAGE.md, API.md, DATA_MODEL.md, DISCOVERY.md, PROTOCOL_EVIDENCE.md,
FINGERPRINTS.md, ENRICHMENT.md, SEARCH.md, SEARCH_BENCHMARK.md, GEOGRAPHIC_UI.md,
MAP_ASSETS.md and INSPECTION.md. Inspect Git status/remotes, actual runtime/Compose
state, existing fixture truth, benchmark scripts, derivation/inspection contracts,
scheduling/worker authority and tests before designing. Never infer delivered modules
from prior chat history or planned roadmap language.

Current delivery: package **0.13.0**, operations request/snapshot **1**, backup manifest
**2** with explicit legacy v1 compatibility; schedule input/plan **1**, coverage-refresh-1
and explicit-authored-seeds-only-1; control envelope **1**; HTTP/local query **1**;
synthetic-preview-1; Settings **3**; observation/manifest **2** with explicit v1 reads;
fingerprint pack/result **1**, fingerprints-1, netatlas-categories-1; enrichment
bundle/result **1**, enrichment-1; Alembic **0006**. Cryptography is **50.0.2** after
Phase 12 advisory remediation; runtime pins remain Python 3.14.7, uv 0.12.19,
Node 26.8.1, npm 11.19.0, PostgreSQL 18.3/PostGIS 3.6.4 and MapLibre 6.12.0.
OpenSearch remains deferred by the small synthetic benchmark. There is no real
input, Internet campaign, public deployment, worldwide worker network, production
OS isolation, encrypted backup or real-world accuracy qualification.

Implement a reproducible evaluation harness and independently labelled authored
corpus, with a clear report of precision/recall, unknowns/ambiguity, latency, throughput,
storage growth, freshness and geography/coverage bias **only within qualified fixture
scope**. Compare outputs to independently authored truth, not the implementation's own
predictions. Define units, denominators, exclusions, sample selection, clocks, seeds,
configuration/dataset/rule/engine provenance, repetition/warm-up and uncertainty before
interpreting results. Distinguish product assertion detection, category candidates and
physical device identity; spoofed markers and incomplete evidence must remain visible.
Report failure cases and gaps as well as successes. Avoid aggregate accuracy numbers
that hide unknown classes, ambiguous candidates, stale/negative sources or seed bias.

Use disposable synthetic DBs, temporary private blobs and bounded loopback fixture
services. Scope computational/load work explicitly; do not relax existing bounds just
to obtain larger numbers. Reuse/extend the Phase 6 benchmark where useful, keeping its
older warm-cache single-client result labelled historical. Measure meaningful complete
operations, separate setup from timed work, preserve exact source/count semantics, and
report environment, resource limits and failure/backpressure. Observed lab throughput
is not worldwide capacity. No paid infrastructure, real datasets/targets, new vantage
network, public listener or Internet sweep is authorized. If real-world evaluation
would improve the thesis, document it as a separately scoped proposal requiring owner
and institutional authorization; finish the synthetic evaluation independently.

Preserve Phase 12 operations. /healthz is liveness, /readyz checks DB/migration/private
blob access and disk reserve; low capacity is degraded, missing dependencies unavailable,
shared read contention can be busy. A deliberate global stop does not mean unready.
Readiness does not verify every blob, permission, backup or independent worker copy.
Fixed-cardinality process HTTP counters/histograms and bounded JSON summaries never
contain endpoints, queries, peer data, operator contacts, secrets or raw exceptions.
Counters reset on restart and are not target-latency/measurement-success statistics.
The separate /operations dashboard manually reads counts through the generated client,
never reconciles leases or changes authority, and clears hidden/60-second snapshots.

Use the existing owner DB connection only for migrations/operator/test administration.
Optional generated service credentials are under ignored data/storage/services/read
and control; the owner volume/password remain unchanged. The read role has explicit
SELECT grants; control has only needed source/job/attempt/pacing/outbox DML. It cannot
enqueue, suppress, reopen, remove observations or change schema. PUBLIC privileges and
same-OS-user access remain trusted-local limitations. Workers get no DB secret.
Provisioning is no-clobber and additive; do not reset credentials to recover. Staged
worker bearer replacement preserves worker UUIDs and boot counters. Keep boot.json.

Local DB pools: two connections, zero overflow, two-second connect/pool waits.
Launchers: one process, 32 concurrent connections/tasks, backlog 32, two-second
keepalive and 16-KiB incomplete-header ceiling. Compose: 1 GiB DB memory, two CPUs,
256 PIDs, three 10-MiB logs; existing Colima VM is 2 CPUs/2 GiB/20 GiB. Blob/spool
publication preserves a 64-MiB filesystem reserve; the DB volume has no disk quota.
Do not fill or disrupt owner storage as a failure test. Keep app/DB error logs private;
SQL/parameter/ordinary DB error logging and HTTP access logs are disabled.

Preserve Phase 11 scheduling: pure offline bounded authored routed/unrouted/unknown
regions, explicit sourced IPv6 seeds, canonical universe/policy/config/seed/input
identities, SHA-ranked sampling, /24-/48 round-robin ordering and explicit round
rotation. Logical shards partition one plan, never worker authority or independent
budgets. Fairness means dispatch order, not successful coverage/latency. Changed
eligibility can bias it. IPv6 denominators are seeds/regions, never exhaustive space.
Planning counts separate excluded/blocked/fresh/eligible/sampled-out/deferred/scheduled
from admitted/measured/incomplete/retained/refreshed sources, never devices/prevalence.

Refresh is a new explicitly scheduled measurement bound to the exact latest retained
attempt UUID/digest, including negative/empty history. Default cooldowns: open one day,
closed seven days, timeout/error two days. New job/attempt/source IDs and ordinary
budgets apply; delivery replay is never refresh. Admission rechecks actual DB history,
suppression, unresolved issued attempts, expiry and queues under the shared lock.
Exact schedule replay returns the original campaign, even cancelled/restored. Issued
attempts without receipts block remeasurement for retained control history; pruning
is explicit, not a retry. Plans expire within 1–3600 seconds and universe validity;
future DB-clock plans fail closed. No unattended scheduling/expiry daemon or UDP.

Executable scope remains enabled operator identity plus explicit lab_loopback,
--synthetic and --measure; only literal 127.0.0.1/::1, at most 16 ports/32 jobs.
No documentation-to-loopback translation. Standalone discovery remains disabled/
dry-run by default, bounded literal/small-CIDR, pinned policy and deny-first opt-outs.
Protocol capture additionally requires measurement.protocol_evidence. No credentials,
auth bypass, exploitation, persistence, remote modification, DNS/SNI, cookies, mail,
STARTTLS, crawling, streams, device commands or amplifying retries. At most two
connections, two GET / requests and one TLS handshake per endpoint.

Preserve two authenticated local worker identities, increasing persisted boot generation
and session fencing. Jobs bind attempt/reserved observation UUID, increasing fence,
lease/hard horizon and delivery session. Only unstarted leases may reassign, at most
three times. Once a permit is issued, loss is uncertain and never automatically
remeasured. Saved original results can recover delivery-only authority within 24 hours;
cancelled/suppressed/reassigned work cannot. Every connection needs a committed one-use
250-ms permit measured conservatively from worker monotonic request start. Delayed/lost
grants burn; waits consume none. Rates and /24-/48 spacing, clock-regression failure,
possible occupied slots and restart pacing persist. At most min(2, concurrency) sockets.
One-second heartbeats renew ten-second leases; control failure normally closes active
I/O within about three seconds, subject to scheduling. No instantaneous physical fencing.

One fsynced pending slot and one stage per worker, each ≤1 MiB; five bounded-backoff
attempts resend identical results. Storage failure preserves backpressure; new boots
reconcile before claiming. One active campaign, 128 pending/1024 retained jobs, two
workers. Control HTTP: 1-MiB delivery, 16-KiB other JSON, depth32, five-second body
limit, eight in-flight exchanges, no Origin/Cookie/CORS/forwarded trust/access logs.
Separate 1-MiB schedule metadata does not enlarge the 12-KiB campaign snapshot.

Global stop durably cancels all work and blocks admission/delivery; allow-new-work
opens only future admission. It never revives jobs, clears suppressions or resets
identity/pacing. Suppression/source removal and matching revocation commit together.
DB outage can prevent committing stop: stop workers locally. Independently handle
worker pending copies, standalone spools, schedules, outputs and backups; offline
copies cannot receive deletion. Keep worker credentials and boot files.

Immutable v1/v2 source blobs plus hash-placeholder JSONB/evidence_refs remain exact.
UUID/canonical digest distinguishes replay/conflict. Fsynced blobs precede synchronous
commit; source/projection/outbox/job receipt share one transaction/advisory lock, then
acknowledge. Readers, GC, maintenance and backup coordinate. Never edit shipped
migrations. No external exactly-once outbox effects are implemented. Latest attempt/
open/evidence independently order finish/start/UUID; negatives preserve older evidence.
Derivations remain replayable, direct indexes have no asynchronous deletion-copy lag.

Sources expire after 30 days; actual reads reject expiry before maintenance. Removal
is whole-observation, never rewritten sanitization. Tombstones/removal events and
control/schedule metadata retain 90 days; backups seven days. Manifest 2 rejects bad
age windows; legacy v1 needs independent age review. Backups remain unencrypted and
manually pruned. Restore only into a separate empty DB/blob root, omit ACLs/ownership,
migrate, cancel historical jobs/campaigns, expire leases, set global stop, verify and
reapply current suppressions offline. Explicit service grants/reopening follow review.
Never reset owner state to make tests pass.

Preserve exact endpoint/source UUID/digest/optional source-bound derivation inspection.
Wrong/missing/expired/suppressed identities give generic 404. Verify hashes/trace
pointers/ranges/slices under the lock with retention checks before/after projection.
No arbitrary blob/path/raw download, source export or request-triggered derivation.
synthetic-preview-1 permits reviewed inert UTF-8 only: 2048 original body/greeting bytes,
256 per scalar, visible controls/bidi and allowlisted HTTP fields. Sensitive markers
withhold entire candidates before truncation; no raw/hex/base64 fallback. This is not
comprehensive sanitization or real-input permission. Captured HTML/URLs never execute
or load resources. Bounded DER assertions remain unverified, no extensions/trust/fetch.
Retain all ambiguous fingerprint candidates and exact rule/pack/engine/source traces.

Read schema 1 retains JSON, X-NetAtlas-Read:1 non-secret guard, literal-loopback peer,
approved Host/Origin, no Cookie/CORS/credentials/forwarded trust/access logs. Regenerate
schema.ts using `uv run --locked python -m netatlas.read_api.contract` after intentional
HTTP changes; keep AbortSignal, omitted credentials, redirect refusal and generic errors.
Bounds: 16-KiB JSON/depth32, five-second body, 256-character text, 1–200 rows, 1–50
facets, 2048-character cursors, four-MiB output, one data read, five-second SQL and
normal ten-second lock wait. Keysets bind query/route/finish/start/UUID, last 15 minutes
without renewal and cap traversal at 10000. Live retained views cannot revive removal.

Source choice precedes filters without older-match fallback. Core is the default exact
pack; enrichment requires an explicit dataset hash. Counts separate endpoints/sources/
candidates. Geography is approximate area context, never precise devices, with unknown
radii/provenance. UI has one shared cancellable read lane and displayed page; hidden/
pagehide/60-second expiry clears map/places/selection/inspection/timeline. No persistent
cache, captured resources or push-deletion claim. Timeline includes 20 retained attempts,
including negatives. Keep local map assets, inert rendering and post-React focus.
The approximately 1.304-MB JS/511-kB worker warning is documented. Basemap is Fiji only;
Natural Earth v5.1.2 hashes/licenses remain in MAP_ASSETS. `make demo` expires old data
then appends 13 authored sources/12 endpoints, preserves owner data and prints a fresh
dataset hash valid seed-time minus one day through plus seven days. No auto-download.

Inspect Docker/Compose and dedicated Colima before restarting. Run `make db-up
COMPOSE=docker-compose` and `make db-migrate`; omit override on Compose-plugin hosts.
Preserve native arm64/amd64 PostGIS, volume and secret. `make local-build` and
`make local-serve` provide the same-origin built UI/API at 127.0.0.1:8000 after explicit
service-role provisioning. TLS tests generate ephemeral keys. Browser tests use
ports 8000/5173 and disposable netatlas_test_web_* DBs, temporary roles/blobs; worker
tests use random loopback ports/generated tokens. No unrelated listeners may be killed.

Phase 12 full make check-db passed **385 Python tests, 28 web tests and six production
Chromium tests**, including 11 operational cases, all scheduling/worker/restore checks,
restricted-role production deployment, zero external requests and Axe. Final npm/Python
audits reported no known vulnerabilities within their scope; advisory data changes.
Owner storage remained two sources/one fingerprint/one enrichment after local smoke;
new service credentials exist privately, no owner worker credentials/coordinator were
provisioned. Git/Actions and the completion report identify actual delivery status.

At completion run the reproducible evaluation and meaningful regression checks, full
make check-db, and review tracked files/diff for secrets, captures, outputs and datasets.
Commit authored small corpus/scripts/reports, not measured/generated private outputs.
Update authoritative docs and replace NEXT_PHASE with the complete Phase 14 kickoff.
Commit with a Phase 13 message, push if a remote exists, verify local HEAD equals remote
delivery HEAD and clean tree, inspect CI, report actual results/limitations/commit/push/
blockers and the full next kickoff, then stop. No Phase 14 implementation, release/tag,
public deployment or real-world campaign in this chat.
