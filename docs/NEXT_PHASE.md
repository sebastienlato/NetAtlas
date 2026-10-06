# Post-Phase-14 maintenance / publication handoff

There is **no next implementation phase**. Phase 14's independently deliverable
engineering, thesis demonstration and **public source handoff** are complete.
The owner explicitly authorized public source code only on October 6, 2026. GitHub
is public; classmates use CLASS_DEMO.md to run it locally. No project redistribution
license, public application deployment or tag/release is authorized.
Stop implementation after this handoff. A later chat must have an explicit maintenance
request or applicable owner/university publication and release decisions.

## Self-contained kickoff for a later authorized chat

You are the authoritative developer and project manager for NetAtlas, an independent
university thesis project. Repository files are authoritative. Preserve owner changes;
make routine decisions autonomously and finish independent work before asking about a
genuine blocker. Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md,
DECISIONS.md, CONTRIBUTING.md and SECURITY.md. Then read docs/RELEASE_CANDIDATE.md,
INSTALLATION.md, DEMONSTRATION.md, EVALUATION.md, EVALUATION_REPORT.md, OPERATIONS.md,
DEPENDENCIES.md, SCHEDULING.md, DISTRIBUTED.md, STORAGE.md, API.md, DATA_MODEL.md,
DISCOVERY.md, PROTOCOL_EVIDENCE.md, FINGERPRINTS.md, ENRICHMENT.md, SEARCH.md,
SEARCH_BENCHMARK.md, GEOGRAPHIC_UI.md, MAP_ASSETS.md and INSPECTION.md as relevant.
Inspect actual Git/status/remotes/CI, runtime/Compose and implementation before changes.

Current delivery: **Phase 14 candidate with public source**, package **0.15.0**, health **14**.
Alembic **0006**; evaluation report **1**, thesis-evaluation-1; operations request/
snapshot **1**; backup manifest **2** (explicit v1 compatibility/age review); schedule
input/plan **1**, coverage-refresh-1, explicit-authored-seeds-only-1; control envelope
**1**; HTTP/local query **1**, synthetic-preview-1; Settings **3**; observation/manifest
**2** with explicit v1 reads; fingerprint pack/result **1**, fingerprints-1,
netatlas-categories-1; enrichment bundle/result **1**, enrichment-1. No Phase 14 runtime
dependency or production rule/traffic semantic change. Pins: Python 3.14.7, uv 0.12.19,
Node 26.8.1, npm 11.19.0, PostgreSQL 18.3/PostGIS 3.6.4, MapLibre 6.12.0,
cryptography 50.0.2. Do not edit shipped migrations.

## Demonstration and reproducibility

`make thesis-demo` is explicit, additive and authored, with no target traffic.
It runs normal expiry then appends **16 sources / 15 endpoints**, with 16 fingerprint
and 16 enrichment results in fresh storage. Current attempt has **15 sources /
13 candidate records**, 11 mapped points and four unknown points. Historical attempts
have 16 sources/14 candidates. Exact source choice precedes filters. Default
`make demo` remains **13 sources / 12 endpoints**. Repeated seeding appends history.
Use separate disposable storage for exact walkthrough counts. Seed prints canonical
dataset hash, clock and validity from seed minus one day through plus seven days.

The additional thesis fixtures are authored stale nginx at 203.0.113.14:80, two
product/role candidates at 203.0.113.15:80 and closed .16:80. The existing 192.0.2.1
negative timeline preserves its prior evidence. All addresses are documentation
fixtures, never executable targets. Use actual card UUID/digest/derivation identity;
never mix sources or reuse an old run's IDs. Approximate geography and unknown radii
remain explicit. Fiji-only basemap, page-only clusters, no persistent UI cache.

INSTALLATION records a fresh local clone with empty dependency caches, online locked
install/build, then deleted disposable venv/node_modules recreated successfully with
UV_OFFLINE=1/npm_config_offline=true. A fresh Compose project/volume/secret/roles on
port 55433 used the acquired pinned image with `--no-build --pull never`. Existing
host tools and Chromium were reused. No virgin-machine, uncached image/OS build or
host-wide air gap is claimed. Colima requires a VM-shared checkout for secret mounts;
macOS private /var/folders failed and was corrected without owner changes. Initial
runtime/package/image/browser downloads and advisory/Git/CI network needs are explicit.
Explorer/operations require no external resources; optional Swagger /docs uses a CDN.

`make local-build` and `make local-serve` are the built same-origin loopback path,
after explicit no-clobber service-role provisioning. The read role serves UI/API;
owner commands retain migration/admission/stop/suppression/backup authority. The
separate control role cannot enqueue, reopen, suppress or change schema. No worker
DB secret, persistent owner coordinator or owner worker credentials were provisioned.
Do not reset owner volume/password, role grants or worker boot generations.

Presentation sources are docs/presentation/build.mjs and README.md; the editable
12-slide deck, notes and screenshots remain ignored/private under artifacts/phase14.
The read-only `node docs/presentation/rehearse.mjs DATASET_SHA256` uses installed
Playwright Chromium, an already-running fresh thesis demo and literal port 8000.
It checks counts/history/stale/unknown/ambiguity/operations and refuses external
requests. Its private source identity ledger and screenshots are independent copies.
The deck authoring library comes from Codex's Presentations runtime, not NetAtlas.
Follow the artifact skill again if revising the exported presentation.

## Verified evidence and validity limits

October 6 source-publication maintenance reran the complete checks below and the
fresh isolated thesis browser walkthrough successfully. Dependency audits found no
known findings. All 21 prior commits and 21 Actions log archives were reviewed for
secrets; eight history matches were generated OpenAPI checksum comments. GitHub
secret scanning/push protection, dependency alerts and private vulnerability reporting
are enabled. Read PUBLICATION.md for scope and limitations. Runtime is unchanged.

Full **make check-db COMPOSE=docker-compose** passed **396 Python tests, 28 web tests,
six production Chromium tests**, plus static/type/format/contract checks, builds and
CLI smoke. Two old public-directory fixtures now chmod explicitly, so private umask
077 cannot accidentally make the public-directory rejection test private. Production
permission behavior is unchanged. A final inventory check also found forced browser-test shutdown bypassing cleanup.
Playwright now requests bounded graceful SIGTERM, with a returning outer handler
for Uvicorn's signal re-raise. Only identified prior test DB/role/temp leftovers
were removed; final shutdown leaves the owner inventory unchanged. Actual restricted-role thesis browser rehearsal
passed with **zero external requests**, exact source identities and reviewed screenshots.

One-repetition/two-query-sample evaluation recheck at **2026-10-05T18:01:39.226760Z**
passed classification, exact functional/geographic/coverage and backpressure oracles,
plus four completed standalone loopback sources/four connections/three candidates/
one unknown/zero incomplete. A future-clock attempt failed closed; a DB-derived
recent clock succeeded. Full machine-readable outputs remain private. Fresh advisory
audits found zero known Python/npm findings in installed-package scope, excluding
unpublished NetAtlas and not covering the OS/container. See RELEASE_CANDIDATE.

Preserve the original Phase 13 report as a separately qualified historical result:
30 same-author purposive scenarios labelled independently of predictions/rule IDs,
not blind/second-rater/random truth. Assertion precision nginx 6/6, OpenSSH 3/3,
Postfix 1/1, Apache undefined; recall 6/7, 3/4, 1/1, 0/1. Role scoring is separately
lower, eight unsupported classes remain misses; 21/30 unknown outputs, one multiple
product/role source. Spoofed markers do not establish latent or physical identity.
Nominal intervals expose small denominators, not population confidence.

Three repetitions/ten complete query samples after warm-up at 128 endpoints/384
sources: current-evidence p50 7.878–8.317 ms, evidence-history 14.163–14.305 ms;
three-commit durable source pipeline 108.6–112.5 sources/s, separate standalone
four-service loopback pipeline 1.298–1.306 sources/s. Small local warm-cache single-client
findings, never distributed/global/sustained capacity. Relations including indexes
565,248 to 4,276,224 B, only 94 logical bytes/two repeatedly shared blobs. No realistic
storage slope or measured worldwide costs. Older Phase 6 remains historical.
OpenSearch remains deferred. No external institutional study has run.

## Boundaries to preserve

Never add credential guessing, authentication bypass, exploitation, persistence,
remote modification or unauthorized measurement. No Internet sweeps, real ingestion,
public listener, paid infrastructure, live routing or new vantage network. Default
fixtures are authored documentation/loopback data. Collection and queries stay separate.

Distributed execution needs explicit enabled identity, lab_loopback, --synthetic,
--measure and only literal 127.0.0.1/::1, at most 16 ports/32 jobs. Two stable worker
identities, persisted increasing boots/session fences, one active campaign, 128 pending/
1024 retained jobs, min(2,concurrency) sockets. Every connection needs a committed
one-use 250-ms permit; delayed/lost grants burn. Only unstarted leases reassign, at
most three assignments. Issued uncertainty never automatically remeasures. Original
saved results may recover delivery-only authority within 24 hours. One fsynced pending
slot plus stage per worker, each <=1 MiB, five identical delivery retries. Keep boot.json.

Protocol ceilings remain two connections, two GET / requests, one TLS handshake per
endpoint; no DNS/SNI, credentials/cookies/authentication, mail/STARTTLS, crawling,
streams/device commands, compression decoding, retry amplification or UDP. One-second
heartbeats/ten-second leases normally stop active I/O within about three seconds of
control failure, subject to scheduling; no instantaneous physical fencing claim.

Offline coverage uses authored routed/unrouted/unknown universes, explicit IPv6 seeds,
exact input/universe/policy/config/seed hashes, SHA sampling, /24-/48 dispatch fairness
and explicit round rotation. Shards partition one budget. Latest retained attempt,
including negatives, controls refresh; exact UUID/digest binds a new measurement.
Unreceipted issued attempts block remeasurement for retained control history. Keep
excluded/blocked/fresh/eligible/sampled-out/deferred/scheduled/admitted/measured/
incomplete/retained/refreshed populations separate. No autonomous scheduler/expiry daemon.

Global stop cancels old authority and blocks admission/delivery. Reopening permits
only future work. Suppression/removal revokes jobs atomically. DB outage can prevent
committing stop: stop cooperative workers locally. Independent spools, pending copies,
outputs and backups require separate removal. Do not erase credentials/boot identities.

Immutable v1/v2 source blobs, hash-placeholder JSONB and canonical UUID/digest replay
identity remain exact. Blob fsync precedes synchronous commit; source/projection/outbox/
receipt share a transaction/lock, ACK follows. Latest attempt/open/evidence order
finish/start/UUID independently. Source expiry 30 days, tombstone/control metadata 90,
backups seven. Reads reject expiry before maintenance. Whole-observation removal,
not silent evidence rewriting. No external exactly-once effect or forensic erasure.

Restore only to a separate empty DB/blob root, omit ACL/ownership, migrate, cancel
historical jobs/campaigns, expire leases and set global stop before verification and
current suppression review. Provision reviewed destination grants explicitly. Backups
remain unencrypted/manually pruned. Never share blob roots or reset the owner to test.

Inspection binds literal endpoint, source UUID/digest and optional derivation; wrong/
missing/expired/suppressed identities give generic 404. Verify hashes/pointers/slices
and recheck retention under the lock. synthetic-preview-1 shows reviewed inert UTF-8
only, 2048 body/greeting bytes, 256 per scalar, visible controls, allowlisted HTTP
fields. Withhold whole recognized-sensitive candidates before truncation. No arbitrary
blob/raw/hex/base64 fallback, captured resource loads or request-triggered derivation.
DER assertions remain unverified. This is not comprehensive sanitization.

Read schema 1 preserves loopback peer/Host/Origin, nonsecret X-NetAtlas-Read guard,
no Cookie/CORS/forwarded trust/access logs, bounded JSON and generic errors. One shared
cancellable read lane, original-query signed keysets (15 minutes/10000 traversal),
200 maximum rows, 4-MiB output, five-second SQL. Hidden/pagehide/60-second expiry clears
map/results/selection/inspection/timeline. No instant push-removal claim. Retention
always wins over historical clocks. Exact pack/dataset selection, unknown radii and
all ambiguous candidates remain visible. Approximately 1.304-MB JS/511-kB worker warning
persists. Natural Earth v5.1.2 notices/hashes remain in MAP_ASSETS.

## Authorized next action only

Public source sharing is complete. Any future license, tag/release, public hosted
application or real measurement requires its own applicable owner decision. Do not
infer those decisions from public source visibility. No new phase is authorized.

For later maintenance, work only on the explicitly requested fix, preserve state and
run proportionate checks. Review tracked files for secrets/data/outputs, update these
authoritative records, commit, push to the existing public remote if applicable,
verify remote HEAD and clean tree, inspect CI and report honestly. The completion
report/Git history identify the final Phase 14 commit; do not invent a circular hash
here. No new roadmap phase, release automation or recurring follow-up is authorized.
