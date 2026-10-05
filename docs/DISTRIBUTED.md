# Phase 10 — local distributed measurement

Package **0.11.0**, control envelope **1**, Alembic **0005**. Two independent local
worker processes use an authenticated coordinator on literal loopback. This is a
bounded synthetic laboratory implementation, not global collection, public access,
production role isolation or a benchmark of distributed throughput. No paid service,
broker, routed-space sampling, UDP, refresh scheduler or real-input ingestion is added.

## Run explicitly

Use the existing database volume, private secret and native PostGIS image:

```sh
make db-up COMPOSE=docker-compose
make db-migrate
uv run --locked netatlas-control provision
uv run --locked netatlas-control serve
```

Compose-plugin hosts omit the override. Provisioning creates a **new empty** private
`data/control/credentials/` directory containing `coordinator.json`, `worker-1.json`
and `worker-2.json`. Files are 0600, directories 0700; existing credentials are never
replaced. Each worker has a random UUID and a separate generated 256-bit bearer
credential. No token is printed, stored in PostgreSQL, included in configuration
hashes or committed. The coordinator's file contains both credentials; each worker
reads only its own. Protect these ignored files and never put tokens in arguments.
Workers need no database credential. OS/DB administrators and credential holders
remain trusted; authentication does not sandbox a malicious worker.

Start an **authored fixture** on literal 127.0.0.1 or ::1. Prepare ignored
`config/local.toml` from the existing defaults with enabled operator identity and
research User-Agent as in DISCOVERY. Set `measurement.protocol_evidence=true` only
when protocol capture is intended. Preview, then explicitly enqueue its port:

```sh
uv run --locked netatlas-control enqueue --config config/local.toml --lab-loopback --target 127.0.0.1 --port 8080
uv run --locked netatlas-control enqueue --config config/local.toml --lab-loopback --target 127.0.0.1 --port 8080 --synthetic --measure
```

Preview opens no database, spool or socket and prints scope/config/policy. Without
`--measure`, nothing is enqueued. Enqueue also requires `--synthetic`, enabled identity
and literal-loopback lab scope. Public/documentation/private targets and loopback CIDRs
are rejected by the distributed adapter; the older standalone discovery interface
retains its existing literal-IP/small-CIDR policy. The narrower worker boundary prevents
accidental real ingestion. Synthetic flags cannot establish that peer content is authored.

Launch the workers in two terminals **after enqueueing**:

```sh
uv run --locked netatlas-control worker --credential data/control/credentials/worker-1.json --spool data/control/worker-1
uv run --locked netatlas-control worker --credential data/control/credentials/worker-2.json --spool data/control/worker-2
```

Each drains available jobs and exits when idle. This is not a continually polling
daemon. Reuse the exact credential and spool paths on restart; the durable boot
generation must not be reset. `serve` and `worker` support `--port` (default 8001).
The coordinator binds only 127.0.0.1. CLI `--storage` selects trusted local DB/blob
settings for operator commands, not workers. No UI/read API can enqueue or cancel.

```sh
uv run --locked netatlas-control status
uv run --locked netatlas-control cancel --campaign CAMPAIGN_UUID
uv run --locked netatlas-control prune
```

Status reports state counts and reconciles expired leases. Cancel is durable and
irreversible for that campaign; it stops further authority, including late delivery.
It does not erase previously committed observations: use ordinary suppression/removal
for that. Prune removes control jobs/attempts/campaign metadata older than 90 days;
it preserves worker generations and pacing. No automatic queue or history scheduler.

## Identities, states and fencing

A campaign pins non-secret Settings v3, Scope, configuration SHA-256, the current
connection policy hash and deadline. A job identifies one TCP endpoint within it.
Each assignment has an independent attempt UUID, monotonically increasing job fence,
reserved observation UUID, stable worker UUID, boot session UUID and delivery session.
Results retain their original observation UUID, timestamps, canonical digest and
source version throughout retry; an equal body never merges separate measurements.

Registration requires the provisioned worker credential. A private, fsynced worker
boot counter increases before each registration. Equal generation/session registration
is idempotent; older or equal-but-different sessions are rejected. A newer registration
expires the previous boot's measurement authority. Reordered registration cannot bring
an old boot back. At most two stable worker identities can register in this database.
Credential replacement/recovery is an operator action, not an automatic third worker.

Jobs move from `queued` to `leased`, then `measuring` after the first permit. A result
commit sets `delivered`. Explicit cancellation/suppression sets `cancelled`. If an
unstarted lease expires, the job is queued with a **new** attempt, fence and observation
UUID on reassignment; after three assignments it becomes `failed`. A permit-issued
attempt instead becomes `uncertain` on lease expiry, hard timeout or worker restart.
It is **never automatically remeasured**, even if the grant acknowledgement was lost
and the worker believes it did not dial. This favors traffic safety over completeness.

Heartbeats renew a 10-second durable lease once per second, within the fixed campaign
deadline. A first permit sets a nonrenewable hard endpoint horizon. Reclaim never gives
an issued job new measurement authority. Its possible socket slot remains occupied
through that horizon even after worker loss or cancellation. Successful delivery can
release it earlier because the compliant collector has already closed its sockets.
Coordinator process restart retains leases, sessions, fences and pacing in PostgreSQL.

The same current boot may deliver after lease expiry, within 24 hours of claim, if
its original issued attempt still owns the job. A restarted boot must explicitly
`resume` **delivery only** for that exact worker/job/attempt/fence. Resume never grants
a connection or revives cancelled/reassigned work. Old sessions, wrong worker, wrong
endpoint, changed UUID/digest/config/campaign or inconsistent connection evidence fail.
Five seconds of source-clock tolerance is allowed around the recorded attempt horizon;
this does not extend permit or lease authority. Source expiry/suppression/tombstones
still apply. A receipt does not bypass blob-integrity checks or resurrect removal.

## Central traffic admission

One PostgreSQL transaction/advisory lock serializes authority, shared pacing, ingestion,
readers, maintenance and backups. Every connection, including a second TLS connection,
requires its own committed, one-use permit. Permit number must equal the previous
count plus one and cannot exceed the campaign's connect-only/protocol cap. A duplicate
permit request is rejected; lost grants are burned, never retried as measurements.
A `wait` reply consumes no permit and may be retried after its bounded delay.

A grant is usable for at most **250 ms measured conservatively from the worker's
monotonic request-start time**. A slow or lost response is abandoned without dialing.
The DB reserves the entire possible start window **plus** the global and /24 IPv4 or
/48 IPv6 spacing. Thus late grant responses cannot collapse spacing into a burst.
Changed rates also respect the previous admission with the new interval. Clock
regression before the last admission fails closed. The effective connection rate is
intentionally below the requested maximum; no throughput optimization is claimed.

Only one active campaign is accepted; all campaigns nevertheless share durable pacing
and occupied socket slots. Concurrency is at most min(2, configured concurrency).
The existing collector still caps an endpoint at two connections, two GET / requests
and one TLS handshake, with cumulative payload/deadline limits. Configured exclusions,
opt-outs, pinned policy and persistent DB suppression are checked centrally before
every permit; the worker checks its pinned policy again immediately before dialing.
No DNS/SNI, redirects, cookies, authentication, mail, STARTTLS, streams, commands,
protocol retries or scope expansion are added.

Loss of coordinator/database/heartbeat access causes the worker to stop admitting and
cancel its active collector; the HTTP client times out after two seconds. With a
one-second heartbeat interval this is normally within about three seconds, subject to
process scheduling. Cancellation/suppression is not instantaneous remote socket fencing:
an already-issued 250-ms permit may still start, and a previously admitted connection
may finish or close at heartbeat/deadline. Paused processes, a malicious credential
holder, physical power failure and arbitrary clock changes are not qualified safety
or durability cases. The target itself has no fencing-token interface. These bounds
are for the supplied cooperative local workers, not hostile remote execution.

## Commit, retry and backpressure

Each worker owns one locked private spool slot. It fsyncs a lease reservation before
requesting traffic and atomically replaces it with the complete immutable delivery
before any send. File contents and containing directory are fsynced. A hard kill can
leave no result, a reservation, or a complete result; it cannot authorize repeating
the measurement. Incomplete staging files are discarded under the spool lock. Missing
results become uncertain; complete results are replayed with their original identity.
The boot file remains even when the pending slot is cleared.

Delivery authority checks, blob publication, observation/current-pointer/outbox writes,
source digest receipt and job completion share **one** storage transaction. Fsynced
blobs precede synchronous commit; the HTTP acknowledgement follows it. The Pipeline's
internal transaction adapter preserves standalone ingestion behavior. A pre-commit
failure rolls everything back (private orphan blobs can remain for locked GC); a lost
post-commit acknowledgement replays and verifies the already committed original.
No separate broker or external outbox consumer is claimed. Existing same-DB consumer
receipts and derivation replay remain unchanged.

Delivery uses at most five attempts per worker run, with 0.25/0.5/1/2-second backoff.
Only transient HTTP/storage failures retry. A failed run retains its complete slot and
exits; restart retries delivery before claiming anything. Conflict, cancellation or
expired authority deletes the pending copy and stops the run. Authentication failure
preserves it for operator recovery. Retry never invokes the collector. Storage unavailability
can leave at most one completed result per worker, not an unbounded memory/disk queue.

| Resource | Bound |
| --- | --- |
| Registered workers / active sockets | 2 / min(2, configured concurrency) |
| Pending jobs / retained jobs | min(128, configured queue_size) / 1024 |
| Current lab scope | At most two literal loopbacks × 16 ports = 32 jobs |
| Assignments / permits | At most 3 assignments; once any permit issued, no reassignment; 1 or 2 permits |
| Control JSON / non-delivery JSON / nesting | 1 MiB / 16 KiB / 32 levels; duplicate keys rejected |
| Campaign snapshot | 12 KiB, including non-secret settings and scope |
| Concurrent HTTP requests / body deadline | 8 per coordinator process / 5 seconds |
| Worker response / HTTP timeout | 64 KiB / 2 seconds; no redirects/proxies/cookies |
| Spool | One pending file ≤1 MiB, at most one ≤1 MiB stage, small boot/lock files |
| Lease / permit / delivery horizon | 10 seconds / 250 ms / 24 hours from claim |
| Control history / source / tombstone / backup | 90 / 30 / 90 / 7 days respectively |

The queue is one bounded explicit scope; fullness rejects new work. There is no bulk
real-data upload, silent spill queue, copied dead-letter payload, refresh scheduling
or broker. SQL retains the shared 10-second lock wait and 60-second statement bound;
worker timeouts may abort safely earlier under contention. One lock remains a deliberate
correctness bottleneck, not a scalable concurrent control/read design.

## Authentication, copies and restore

`POST /control/v1/exchange` is separate from port-8000 read routes. It requires exact
literal loopback peer/Host, JSON, worker identity and its bearer secret; Origin,
Cookie, content encoding and wrong authority fail. No CORS, browser controls, forwarded
trust, access logs, public listener or credential echo. Errors are generic. TLS and
production access roles remain Phase 12; loopback bearer transport is not for forwarding.
The UI's non-secret X-NetAtlas-Read guard remains unchanged and does not authenticate
control requests. All read/inspection/retention semantics remain unchanged.

Persistent DB suppressions are consulted on claim reconciliation, heartbeat and every
permit/delivery. Already saved worker copies are independently owned: after a removal,
cancel/stop both workers, remove their `pending.json` and `pending.stage` copies, and
handle standalone discovery spools/outputs/datasets/backups separately. **Keep boot.json
and credentials**; deleting the boot generation is not a restart procedure. An offline
worker cannot receive deletion; quarantine its spool until reconciled, and never send
it to another project/service. Delivery expiry is an admission bound, not automatic
offline file erasure. Unlink is not forensic erasure. Full distributed opt-out/coverage
scheduling remains Phase 11.

Backups include control metadata/fences but no credential files or worker spools.
Restore into a separate empty database cancels **all restored jobs/campaigns** and
expires their leases before verification. It never resumes a historical measurement
queue. Keep that destination offline until the entire restore succeeds; reapply current
suppressions before use. Continue to apply the seven-day backup and copy quarantine
policy. Existing owner volumes/data are never reset by phase setup or acceptance.

## Validation

`tests/test_control.py` exercises authentication and bounded envelopes; idempotent and
reordered registration; lost claims, fencing and bounded pre-admission reclaim; late
results and delivery-only restart; central IPv4/IPv6/global/per-prefix pacing and TLS
second connections; concurrency after worker loss/cancellation; transactional rollback
and lost acknowledgements; identity conflict, retention, suppression, deadline and
clock regression; spool permissions/backpressure; heartbeat/cancellation socket closure;
populated 0004 upgrade and backup/restore quarantine.

Two actual local worker subprocesses collect authored HTTP/TLS fixtures through the
real authenticated HTTP coordinator and shared PostgreSQL. Both lose a first delivery
acknowledgement without an extra connection or outbox event. A separate subprocess is
killed during a fixture interaction and restarted with the same spool; its single
issued attempt remains uncertain and the endpoint is not remeasured. Full phase checks
passed with 348 Python tests, 26 web tests and five production Chromium tests;
full details are recorded in PROJECT_STATE. No Internet sweep or real input is used.
