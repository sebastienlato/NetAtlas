# PHASE 14 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global Internet
Exposure Search & Visualization, an independent university thesis project. Complete
exactly **Phase 14 — Thesis-ready demonstration/release** in this fresh Work chat.
Repository files are authoritative; preserve owner changes and make routine engineering
decisions autonomously. Complete independent authorized work before asking about a
genuine blocker. Do not run real campaigns, publish publicly or create a tag/release
without the owner's explicit applicable authorization and publication/license decisions.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md and SECURITY.md, then docs/EVALUATION.md, EVALUATION_REPORT.md,
OPERATIONS.md, DEPENDENCIES.md, SCHEDULING.md, DISTRIBUTED.md, STORAGE.md, API.md,
DATA_MODEL.md, DISCOVERY.md, PROTOCOL_EVIDENCE.md, FINGERPRINTS.md, ENRICHMENT.md,
SEARCH.md, SEARCH_BENCHMARK.md, GEOGRAPHIC_UI.md, MAP_ASSETS.md and INSPECTION.md.
Inspect status/remotes, runtime/Compose state, actual implementation and fixture/test
contracts. Never infer delivered modules from planned roadmap language or chat history.

Current delivery is **Phase 13 complete**, package **0.14.0**, health phase **13**,
evaluation report schema **1**, workload **thesis-evaluation-1**. Operations request/
snapshot **1**, backup manifest **2** with explicit v1 compatibility; schedule input/
plan **1**, coverage-refresh-1 and explicit-authored-seeds-only-1; control envelope **1**;
HTTP/local query **1**, synthetic-preview-1, Settings **3**, observation/manifest **2**
with explicit v1 reads; fingerprint pack/result **1**, fingerprints-1, taxonomy
netatlas-categories-1; enrichment bundle/result **1**, enrichment-1; Alembic **0006**.
Pins: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0, PostgreSQL 18.3/PostGIS
3.6.4, MapLibre 6.12.0, cryptography 50.0.2. No new Phase 13 runtime dependency.

Deliver a reproducible seeded offline end-to-end thesis demonstration, installation/
local deployment guidance, architecture/evaluation evidence, a release checklist and
presentation-ready material. Rehearse a fresh installation in an isolated checkout/
disposable storage with the pinned prerequisites, documenting what truly requires
initial downloads and what works offline afterward. Preserve the existing owner
checkout, volume, secret, service roles and private data. The demo should visibly
connect bounded authored collection, immutable source history, fingerprint uncertainty,
approximate geography, search/map/timeline/inspection, worker/schedule semantics and
operations without implying that every screen action runs all stages. Demonstrate
negative/stale/unknown/ambiguous cases as well as successes. Keep read UI free of
measurement controls. Use ordinary documented entry points and exact source identities.

Prepare concise walkthrough/presentation material, screenshots/diagrams as useful,
architecture and limitations/cost discussion, reproducibility commands and acceptance
checklist. Follow applicable artifact skills when creating decks/documents. Do not
invent external validation, hosted deployment, global workers, broad device detection,
measured worldwide costs or a comprehensive sanitizer. There is no selected project
redistribution license. Finish all independently deliverable work, then ask only for
unavoidable owner/university publication/license or release decisions. Preparing a
reviewable release candidate does not itself authorize public publication or tagging.
Do not create an unrequested next roadmap phase.

## Evaluation evidence to preserve

Phase 13 includes a separately labelled **30-case authored corpus** and explicit
protocol fixed before the reported run. Labels are independent of predictions/rule
IDs, not a second-rater/blinded/random sample. Product assertions, scenario roles and
latent-software counterexamples have separate denominators; physical-device identity
is not evaluated. Unsupported classes, null truth, unknown output, duplicates and
multiple candidates remain visible. Production core rules were not tuned to the corpus.

At 2026-10-05T17:07:00Z, three disposable DB repetitions with 10 timed queries per
shape after one warm-up used 32/128 endpoints and 96/384 sources. Current-evidence
p50 was 7.878–8.317 ms; evidence-history p50 14.163–14.305 ms. Three-commit durable
source pipeline throughput was 108.6–112.5 sources/s. Four-service standalone
loopback capture/spool/ingest/derive/search was 1.298–1.306 sources/s under default
pacing; this is not distributed-worker throughput or a sustained/global rate.
Relations including indexes grew from 565,248 B to 4,276,224 B; two repeated blobs
used only 94 logical bytes, an intentionally unrealistic deduplication-heavy input.
Do not extrapolate these local warm-cache single-client results. Phase 6's older
2,048-endpoint benchmark remains explicitly historical. OpenSearch remains deferred.

Core product-assertion recall: nginx 6/7, OpenSSH 3/4, Postfix 1/1, Apache 0/1;
precision 6/6, 3/3, 1/1, undefined respectively. Category-role precision/recall is
separately lower; eight unsupported classes are misses. 21/30 cases yield no
candidates; one preserves multiple products/roles. Spoofs detect the marker but
misstate latent identity/role. Nominal intervals expose tiny denominators, not real
population confidence. Six-source geographic view has four points, two gaps and
three unknown radii among the four points. Seedless IPv6, sample/queue exclusions
and exact latest-negative freshness remain explicit. Use the report's detailed
provenance/failure ledger, not one misleading aggregate accuracy score.

Reproduce with a recent aware UTC --at and a NEW ignored output:
`uv run --locked python -m netatlas.evaluation --at RECENT_AWARE_UTC --synthetic --measure --output data/thesis-evaluation-NEW.json`.
Without --measure the harness skips fixture network collection. Default/max is
three repetitions and 10 samples/query, fixed 128 endpoints; no bounds are relaxed.
It uses newly named netatlas_test_eval_* DBs, private temporary blobs/spools and
mode-0600 no-clobber JSON. Commit authored analysis, not measured outputs/datasets.
Normal cleanup removes owned fixtures; abrupt termination may need targeted cleanup.
External institutional validation is an unexecuted separately authorized proposal.

## Existing runtime and operations

Inspect Docker/Compose and dedicated Colima before starting/restarting. Use
`make db-up COMPOSE=docker-compose` and `make db-migrate`; omit the override on
Compose-plugin hosts. Preserve native arm64/amd64 PostGIS, named volume and password.
Existing Colima: 2 CPUs/2 GiB/20 GiB. DB container: 1 GiB, two CPUs, 256 PIDs,
three 10-MiB logs. DB pools: two connections, zero overflow, two-second waits/connect.
Launchers: one process, 32 concurrent tasks/connections, backlog 32, two-second
keepalive, 16-KiB incomplete-header ceiling. Blob/spool reserve is 64 MiB; the DB
volume has no quota. Do not fill/disrupt owner storage for failure demonstrations.

Owner connection is only for migrations/operator/test administration. Optional
private service credentials exist under ignored data/storage/services/read and
control. Read has explicit SELECT; control has only necessary source/job/attempt/
pacing/outbox DML, cannot enqueue, suppress, reopen, delete sources or change schema.
No worker DB secret. Provisioning is additive/no-clobber; never reset credentials
to recover. Same-OS-user access and inherited PUBLIC privileges remain trusted-local
limitations. Worker bearer replacement preserves UUIDs/boot generations; keep boot.json.
No persistent owner coordinator or worker credentials were provisioned by Phase 13.

`make local-build` and `make local-serve` serve built UI/API at 127.0.0.1:8000 through
the restricted read role after explicit provisioning. /healthz is liveness; /readyz
checks DB/migration/private blob access/reserve. Low capacity is degraded, missing
dependencies unavailable, shared read contention busy. Global stop is not unready.
Readiness does not verify every blob, permission, backup or independent copy.
Fixed-cardinality HTTP telemetry contains no endpoints, queries, peers, contacts,
secrets or raw exceptions; counters reset on restart and do not measure target
latency/success. The separate /operations dashboard manually reads counts, never
reconciles authority, and clears hidden/60-second snapshots. Keep app/DB logs private;
SQL/parameter/ordinary DB error and HTTP access logging remain disabled.

## Measurement, scheduling and worker authority

No credential guessing, auth bypass, exploitation, persistence, remote modification,
real datasets/targets, paid infrastructure, public listener, Internet sweep or new
vantage network. Default tests are authored documentation-address/loopback fixtures.
Executable worker scope requires enabled operator identity, explicit lab_loopback,
--synthetic and --measure; only literal 127.0.0.1/::1, at most 16 ports/32 jobs.
Never translate documentation IPs into executable loopback plans. Discovery defaults
disabled/dry-run, bounded literal/small CIDR, deny-first pinned policy and opt-outs.
Protocol evidence needs its separate opt-in. At most two connections, two GET / requests
and one TLS handshake/endpoint. No DNS/SNI, cookies, authentication, mail, STARTTLS,
crawling, streams, device commands, compression decoding or amplifying retries. No UDP.

Offline scheduling accepts bounded authored routed/unrouted/unknown regions and
explicit sourced IPv6 seeds, with exact universe/policy/config/input/seed identities,
SHA-ranked sampling, /24-/48 round-robin order and explicit round rotation. Logical
shards partition one plan and never multiply budgets or worker authority. Fairness
is dispatch order, not successful coverage/latency; changed eligibility biases it.
IPv6 denominators are seeds/regions, never exhaustive space. Keep excluded/blocked/
fresh/eligible/sampled-out/deferred/scheduled distinct from admitted/measured/incomplete/
retained/refreshed sources, never devices/prevalence. No autonomous scheduler/expiry daemon.

Refresh is a new scheduled measurement bound to exact latest retained source UUID/
digest, including negative/empty history. Defaults: open one day, closed seven days,
timeout/error two days. New job/attempt/source IDs use ordinary budgets; replay is
never refresh. Admission rechecks DB history, suppression, unresolved issued attempts,
expiry/queues under the shared lock. Exact schedule replay returns the original
campaign, even cancelled/restored. Unreceipted issued attempts block remeasurement
for retained control history; explicit pruning is not a retry. Plans expire within
1–3600 seconds and universe validity; future DB-clock plans fail closed.

Preserve two authenticated worker identities, persisted increasing boot generations
and session fencing. Jobs bind attempt/reserved observation UUID, increasing fence,
lease/hard horizon and delivery session. Only unstarted leases can reassign, at most
three times. Once a permit issues, loss is uncertain and never automatically remeasures.
Original saved results may recover delivery-only authority within 24 hours; cancelled/
suppressed/reassigned work cannot. Every connection needs a committed one-use 250-ms
permit, conservatively measured from worker monotonic request start. Delayed/lost
grants burn; waits consume none. Global/prefix spacing, clock-regression failure,
possible occupied slots and restart pacing persist. At most min(2,concurrency) sockets.
One-second heartbeats renew ten-second leases; control loss normally closes active
I/O within about three seconds subject to scheduling, not instantaneous physical fencing.

One fsynced pending slot and one stage per worker, each at most 1 MiB; five bounded
identical-result delivery retries. Storage failure preserves backpressure and new
boots reconcile before claiming. One active campaign, 128 pending/1024 retained jobs,
two workers. Control HTTP: 1-MiB delivery, 16-KiB other JSON, depth32, five-second body
limit, eight in-flight exchanges, no Origin/Cookie/CORS/forwarded trust/access logs.
Separate 1-MiB schedule metadata does not enlarge the 12-KiB campaign snapshot.

Global stop durably cancels work and blocks admission/delivery; allow-new-work opens
only future admission, never revives jobs, clears suppression or resets identity/pacing.
Suppression/source removal and job revocation commit together. If DB outage prevents
committing stop, stop workers locally. Independently handle pending copies, standalone
spools, schedules, outputs and backups; offline copies cannot receive deletion. Keep
credentials/boot files. No physical erasure or hostile-worker sandbox is claimed.

## Source, retention, read and UI contracts

Immutable v1/v2 blobs, hash-placeholder JSONB/evidence_refs, UUID/canonical replay
identity remain exact. Fsynced blobs precede synchronous commit; source/projection/
outbox/job receipt share the transaction/advisory lock, then acknowledge. Readers,
GC, maintenance and backup coordinate. Never edit shipped migrations. No external
exactly-once outbox effect exists. Latest attempt/open/evidence independently order
finish/start/UUID; negatives preserve older evidence. Derivations remain replayable;
direct indexes have no asynchronous deletion-copy lag.

Sources expire after 30 days; actual reads reject expiry before maintenance. Removal
is whole-observation, never rewritten sanitization. Tombstones/removal and control/
schedule metadata retain 90 days, backups seven days. Manifest 2 rejects invalid age
windows; legacy v1 needs independent age review. Backups remain unencrypted/manually
pruned. Restore only into a separate empty DB/blob root, omit ACLs/ownership, migrate,
cancel historical jobs/campaigns, expire leases, set global stop, verify and reapply
current suppressions offline. Explicit service grants/reopening follow review. Never
reset owner state to make tests pass or share a blob root between databases.

Inspection binds endpoint/source UUID/digest/optional source-bound derivation. Wrong,
missing, expired or suppressed identities return generic 404. Verify hashes/pointers/
ranges/slices under the lock and recheck retention before/after projection. No arbitrary
blob/path/raw download, export or request-triggered derivation. synthetic-preview-1
permits reviewed inert UTF-8 only: 2048 body/greeting bytes, 256/scalar, visible controls/
bidi and allowlisted HTTP fields. Sensitive markers withhold whole candidates before
truncation; no raw/hex/base64 fallback. This is not comprehensive sanitization or real
input permission. Captured HTML/URLs never execute/load. DER assertions are unverified;
no extensions/trust/fetch. Preserve all ambiguous candidates and exact source/rule/
pack/engine traces; source/dataset identity must never be merged across attempts.

Read schema 1: bounded JSON, nonsecret X-NetAtlas-Read:1 guard, literal-loopback peer,
approved Host/Origin, no Cookie/CORS/credentials/forwarded trust/access logs. Regenerate
schema.ts with `uv run --locked python -m netatlas.read_api.contract` after intentional
HTTP changes; preserve AbortSignal, omitted credentials, redirect refusal/generic errors.
Limits: 16-KiB JSON/depth32, five-second body, 256-character text, 1–200 rows, 1–50 facets,
2048-character cursors, four-MiB output, one data read, five-second SQL, ten-second lock
wait. Query/route/finish/start/UUID-bound keysets last 15 minutes without renewal and
cap traversal at 10000. Live retained views cannot revive removal.

Source choice precedes filters, without older-match fallback. Core is the default
exact pack; enrichment requires explicit dataset hash. Counts distinguish endpoints,
sources and candidates. Geography is approximate area context with unknown radii/
provenance, never precise devices. One shared cancellable UI read lane/displayed page;
hidden/pagehide/60-second expiry clears map/places/selection/inspection/timeline. No
persistent cache, captured resources or push-deletion claim. Timeline retains 20
attempts including negatives. Keep local assets, inert rendering and post-React focus.
Existing approximately 1.304-MB JS/511-kB worker warning remains. Basemap is Fiji-only;
Natural Earth v5.1.2 hashes/licenses remain in MAP_ASSETS. `make demo` expires old data,
then appends 13 sources/12 endpoints without owner reset; printed fresh dataset validity
is seed-time minus one day through plus seven days. No auto-download or auto-seed.

## Validation and phase handoff

Phase 13 full `make check-db COMPOSE=docker-compose` passed **394 Python tests,
28 web tests, six production Chromium tests**: nine evaluation cases plus all worker/
scheduling/operational/restore/integrity checks, restricted-role production deployment,
zero external browser requests and Axe. TLS uses ephemeral keys; worker tests random
loopback ports/generated tokens; browser tests ports 8000/5173 and disposable
netatlas_test_web_* DBs/roles/blobs. Do not kill unrelated listeners. Phase 12 advisory
audits found no known vulnerabilities after cryptography remediation; that record is
historical, not a fresh Phase 13 audit. Recheck appropriately for release readiness.
Owner storage remained **two sources/one fingerprint/one enrichment**; no evaluation
DB remained. Git/Actions and the prior completion report identify delivery/CI status.

Run the reproducible demonstration/rehearsal, proportionate evaluation and complete
make check-db. Review tracked files/diff for credentials, captures, datasets, measured
outputs and accidental release assets. Update authoritative docs and NEXT_PHASE with
the honest final status, remaining manual publication decisions and future maintenance
handoff (no invented next implementation phase). Commit with a Phase 14 message, push
if remote exists, verify local HEAD equals remote delivery HEAD and clean tree, inspect
CI. Only create an owner-authorized release/tag after applicable publication/license
requirements are resolved. Report actual demonstration, checks, artifacts, limitations,
commit/push/CI, release status and any genuine blockers, then stop.
