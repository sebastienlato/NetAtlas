# Phase 12 — local operational hardening

Package **0.13.0**, operations request/snapshot **1**, backup manifest **2** with
legacy v1 reads, migration **0006**. Measurement, source, scheduling, read and
inspection semantics remain unchanged. This qualifies a private synthetic local
laboratory. No public listener, TLS gateway, remote deployment, automatic campaign,
production OS isolation, encrypted backup or worldwide capacity is supplied.

## Reproducible local deployment

Inspect first: `git status --short`, `docker context show`, `colima list`, and
`docker-compose ps` (or `docker compose ps`). Use the existing dedicated Colima
`netatlas` profile on this host; start it with `colima start --profile netatlas` if
stopped. Do not reset a VM, named volume, password or worker boot file. Keep ports
8000, 8001 and 5173 free of unrelated services. Runtime pins: Python 3.14.7,
uv 0.12.19, Node 26.8.1, npm 11.19.0. Install Chromium for browser acceptance with
`npm --prefix web exec -- playwright install chromium` (CI adds `--with-deps`).

For an existing deployment, stop workers and service processes, take a coordinated
backup using the existing image/credentials before changing runtime/container
settings, then build/start using the same named volume and secret:

```sh
make db-up COMPOSE=docker-compose
make db-migrate
uv run --locked netatlas-store expire
uv run --locked netatlas-store verify
make local-build
# Once, to a NEW directory; never overwrites existing accounts or credentials:
uv run --locked netatlas-store provision-access
make local-serve
```

Compose-plugin hosts omit the override. On first installation there is no prior DB
to back up. `expire` creates the private blob root when absent and performs ordinary
retention/GC; it is not a reset. `local-build` installs locked dependencies and builds
both artifacts. `local-serve` uses the generated read account and serves built
`web/dist` plus the API from **http://127.0.0.1:8000**. `/operations` opens the separate
operations dashboard. Vite is unnecessary for this production-build local path;
`make dev-api`/`make dev-web` remain available for development. No automatic demo seed.
`make demo` remains the explicit additive authored seed, requiring owner access.

After ordinary existing worker credential provisioning (DISTRIBUTED), start the
coordinator separately using its DML account and the existing shared blob directory:

```sh
uv run --locked netatlas-control --storage data/storage/services/control --blobs data/storage/blobs serve
```

Enqueue, scheduling, stop/reopen, suppression, pruning, migrations and backups remain
**owner commands using the original data/storage connection**. The coordinator role
cannot enqueue campaigns, clear suppressions or reopen work. Start workers only for
explicitly enqueued authored loopback fixtures, with their original credentials and
spools. Workers still have no DB credential. Processes run in the foreground and
stop with Ctrl-C; no startup service, automatic restart or unattended scheduling.

`netatlas serve --storage PATH --blobs PATH --web-root web/dist` supports a reviewed
alternate credential directory. Paths are trusted operator input, never HTTP input.
Serve only the generated static asset directory. Runtime launchers disable access
logs and forwarded trust, use one process, 32 concurrent connections/tasks, backlog
32, two-second idle keepalive and a 16-KiB incomplete-header parser ceiling. The
existing one-read/eight-control body/SQL limits still govern admitted work. Uvicorn
can return its generic 503 before application telemetry under transport saturation;
not every TCP rejection is counted in application metrics.

## Liveness, readiness and dashboard semantics

| Surface | Access / meaning |
| --- | --- |
| Read `/healthz` | Existing loopback peer/Host/Origin guard; 200 means the process can respond. No dependency, freshness or backup guarantee. |
| Read `/readyz` | Same local guard, no read header needed; 200 ready, 503 degraded/unavailable, or 429 when the shared read lane is occupied. |
| Read `/metrics` | Same guard plus `X-NetAtlas-Read: 1`; fixed process HTTP counters/histograms in Prometheus text format. No DB query. |
| POST `/api/v1/operations` | JSON `{"schema_version":1}`, read header and existing body/output guard; one guarded read lane shared with search/inspection. |
| Control `/healthz`, `/readyz`, `/metrics` | All require the same provisioned worker UUID and bearer credential, literal peer/Host, no Origin/Cookie. No operator mutations or browser access. One independent dependency probe at a time. |

Readiness checks an actual DB query, exact Alembic revision 0006, an existing private
blob directory, directory access and at least 64 MiB available on that filesystem.
Control additionally checks write access. DB connectivity, migration, blobs and
capacity have independent fixed status codes. Low capacity is `degraded`; missing
DB/schema/blob access is `unavailable`. Global stop does **not** make dependencies
unready: a deliberately stopped, healthy system is valid. Readiness does not hash all
blobs, prove table privileges, inspect every worker's spool, measure the container's
separate database filesystem, verify backup freshness or establish safe authority.
Use `netatlas-store verify` for full integrity. No request creates missing directories.

Dependency SQL and lock waits are capped at one second each; local engine connection
and pool waits are two seconds each. These are component bounds, not a hard total
wall-clock SLA under OS/network starvation. The operational aggregate takes the same
pipeline lock with a one-second wait and five-second SQL ceiling. It never reaps
leases or performs maintenance. Failure discards the entire snapshot and returns a
generic error; no stale partial success is labelled healthy.

The dashboard has an explicit Refresh button, one cancellable request, no automatic
polling, and no measurements or mutations. Hidden/pagehide clears results and ignores
late replies; snapshots expire after 60 seconds. Only counts, fixed state labels,
readiness and the DB check clock appear. It preserves these distinctions:

- **Stored jobs** are their last committed states. **Overdue leases** are current
  leased/measuring attempts whose lease has elapsed at the check clock. The read
  does not reconcile them into queued/uncertain jobs or infer new authority.
- **Permits issued** includes burned/late grants and second TLS connections. It is
  neither successful socket starts nor a measured-source count.
- **Delivery receipts** counts committed attempt digests, including observations
  subsequently removed. **Retained sources** counts all currently unexpired,
  unsuppressed sources, including standalone ingestion and negative/empty results.
  These populations overlap and are not additive. Counts are not devices/prevalence.
- **Removal due** counts physically stored expired/suppressed rows. Actual reads
  already reject them. It is not a count of independently owned copies.
- **Outbox events** is stored rows, not external delivery/index lag. Search indexes
  update in the source transaction; no external outbox consumer is implemented.
- **Recent workers** means a DB heartbeat within ten seconds. Idle workers exit;
  zero recent workers is not necessarily a failure and does not prove lost work.
- **Free bytes** is the blob filesystem, not total DB/WAL/backup storage capacity.

Schedule-specific denominators and measured/retained/refreshed counts remain in
`netatlas-schedule report`, with exactly the Phase 11 semantics in SCHEDULING.

## Telemetry and resource limits

Each HTTP service retains a fixed registry: 12 route classes × four status classes,
five finite cumulative latency buckets (0.01/0.1/1/5/15 seconds), +Inf, sums/counts,
active HTTP requests and monotonic uptime. Endpoints are mapped to fixed route
names; arbitrary paths map to `other`. Query values, addresses, ports, worker/source/
campaign IDs, peer content, operator contacts, secrets and exception text are never
labels or log fields. Process counters reset on restart and measure HTTP handling,
not target latency or measurement success. Aborted requests without a response count
as 5xx. No metrics collector, external telemetry exporter or time-series store is
installed. Scrape no faster than once per 30 seconds for this lab.

At most once per 30 seconds **when a request completes**, an allowlisted JSON
`http_summary` log records service, cumulative request/client-error/server-error
counts and uptime. It is not a per-request access log or periodic idle heartbeat.
Logs go to the existing logging sink; no new application log file is created.
Keep redirected logs private, rotate them and discard within seven days. FastAPI
errors and launcher diagnostics remain generic. PostgreSQL statement/parameter and
ordinary error logging are disabled in Compose to avoid payload-bearing errors;
PANIC-level engine diagnostics are not a source of application telemetry.

Local DB engines allow two pooled connections, zero overflow and a two-second pool
wait. Generated roles allow four connections each. Compose caps PostgreSQL at 1 GiB,
two CPUs, 256 PIDs and three rotated 10-MiB local log files; the existing VM is
2 CPUs/2 GiB/20 GiB. The named DB volume has no application quota. Observe its free
space separately with local Docker/Colima administration. A resource kill/outage
returns generic unavailability; cooperative workers stop active I/O on heartbeat
failure under their existing bound. There is no host-wide memory quota for Python.

New blob publication and worker pending-slot writes refuse when free space would
fall below a 64-MiB reserve. Already-existing verified blobs can replay without new
allocation. A denied spool write leaves the prior slot intact; failed ingestion
commits no source/receipt/outbox. This is an early backpressure guard, not a reserved
partition or guarantee against concurrent OS writers. Disk errors remain handled.
Boot/credential recovery files are not blocked by the reserve. Spool files remain
≤1 MiB each, one committed pending slot and one stage, with all Phase 10 limits.

## Access, credentials and recoverable changes

`provision-access` creates new random per-database role names and generated 256-bit
passwords in 0600 files under new 0700 service directories. It never updates owner
passwords or existing roles. Credentials are absent from Settings hashes, SQL log
parameters, console output, Git, DB dumps and worker files. The existing connection
format adds optional username; absent username keeps the owner connection compatible.
Settings/secret files must be bounded private regular files. Secrets are not arguments.

The **read** role has explicit SELECT grants required for search, inspection and
aggregate operations; its default transaction is read-only. The **control** role
has explicit SELECT and limited source/job/attempt/pacing DML and outbox sequence
usage needed for atomic worker delivery. Neither can create/alter/drop schema, create
roles/DBs, bypass row security, change suppressions, migrate, back up, enqueue or
reopen. No new role gets an ownership grant or blanket future-table default grant.
Future migrations require reviewed grants. Provisioning refuses an existing PUBLIC
CREATE privilege on the public schema instead of silently changing owner policy.

This is defense against accidental service writes, **not production isolation**.
Both services still run as the same trusted OS account; it can read owner files.
The read role necessarily sees private source envelopes for inspection; SELECT is
not anonymization. PostgreSQL inherited PUBLIC connect/temp/function privileges
remain; a credential is not a hostile-query sandbox. Container/OS/DB admins and
cooperative worker code remain trusted. Do not forward loopback bearer traffic or
expose services. A public TLS/identity/process-isolation design is out of scope.

Files are fsynced before the atomic role/grant transaction. `complete.json` is written
after commit. If interrupted, keep the newly created files and inspect role existence
and grants using the owner connection; never assume a failed acknowledgement means
rollback. A DB failure rolls back all new roles/grants but leaves recovery files.
Re-run only to a **new** directory after reconciling those roles. Do not delete or
replace owner files to make provisioning pass. Rollback is to stop the new services,
restore their previous launch arguments, and disable/drop only the reviewed newly
created service roles. Existing observation data and worker identities do not change.
A service credential compromise requires owner-side `ALTER ROLE ... NOLOGIN` and
termination of that role's existing DB sessions; NOLOGIN alone does not disconnect.
Provision fresh roles and explicitly switch launch paths. No automatic rotation daemon.

Worker bearer replacement is staged in a fresh private directory and preserves UUIDs:

```sh
uv run --locked netatlas-control stop
# Stop BOTH workers and the coordinator; preserve their spool/boot files.
uv run --locked netatlas-control provision --rotate-from data/control/credentials/coordinator.json --directory data/control/credentials-next
# Restart coordinator with --credentials .../credentials-next/coordinator.json,
# and workers with their corresponding new credential file, SAME original spool.
# Verify readiness and pending-copy/suppression policy before explicitly allowing NEW work.
```

Cutover revokes old tokens at the restarted coordinator; no overlap is accepted by
one instance. Retire old private credential copies after successful cutover. Never
launch two coordinators or reset boot.json to make a new credential work. Recovery
from an incomplete staging write requires a new directory based on the last complete
coordinator file; the old active files are untouched. The local tests verify old-token
rejection, new-token acceptance and strictly increasing boot generation.

## Retention, incident response and restore runbook

Sources expire in 30 days; tombstones/removal events and control metadata retain
90 days; backups and redirected operational logs at most seven days. No maintenance
daemon is installed. At session start and daily while storing data, the owner runs
`netatlas-store expire`, `netatlas-store collect`, `netatlas-control prune`, then
`netatlas-store verify`. Review failed verification before serving. Source reads
already reject expiry/suppression before physical cleanup. Control prune deliberately
removes old unresolved-attempt guards; it is never an automatic refresh/retry action.

On an opt-out or sensitive fixture discovery:

1. Commit `netatlas-control stop`; stop local workers. If DB is unavailable, stop
   workers locally first because a durable stop cannot be committed. Wait for owned
   sockets to close; old grants/in-flight work are not instantaneously fenced.
2. Run `netatlas-store suppress --network CIDR` with the owner connection. Removal
   and matching job revocation share one transaction. Update local opt_out_cidrs and
   regenerate schedules; standalone discovery must also be stopped/configured.
3. Delete/quarantine matching worker pending.json/pending.stage, standalone spools,
   schedule/source snapshot files, outputs and backups, including offline machines.
   **Keep boot.json and credentials.** The DB cannot erase independently held copies.
4. Verify stored sources/projections, review the independent suppression register,
   and explicitly `allow-new-work` only for future authorized work. Reopening never
   revives cancelled campaigns, clears suppression or resets fencing/pacing.

Before backup, run expiry and verification and stop independent operator commands.
Use a new ignored private directory each time:

```sh
uv run --locked netatlas-store backup --output data/storage/backups/session-NEW
```

The shared lock coordinates DB/blob copying against reads/writes/GC; blob hashes,
archive hash, fsync and single-transaction restore remain. Manifest v2 adds creation
and seven-day expiry; expired/future/overlong windows fail restore before any write.
This does not automatically delete old backup files: inventory and remove/quarantine
them daily. Legacy manifest v1 can still restore for historical compatibility, but
has no age proof; the operator must independently establish age ≤7 days before use.
Do not edit dates or downgrade manifests to bypass policy. All SQL archives are
trusted operator input; checksums prove integrity, not origin/authenticity.

Dumps/restores omit role ownership and ACLs, so application grants do not follow a
backup into a recovery database. Credential directories/spools remain independent.
Backups are **unencrypted** and local; protect the OS volume and never upload them.
No PITR/WAL archive, remote replica, physical erasure or production RPO/RTO is claimed.

Restore rehearsal/promotion procedure:

1. Create a **new empty** `netatlas_restore_NAME` DB on the matching local server:
   `docker-compose exec -T db createdb -U postgres netatlas_restore_drill`.
2. Run `netatlas-store restore --input data/storage/backups/session-NEW --database
   netatlas_restore_drill`. It verifies archive/blobs, restores atomically, migrates,
   cancels all historical campaigns/jobs, expires leases, sets global stop, expires
   old sources and verifies hashes/derivation replay. The CLI uses a separate blob
   root under data/storage/netatlas_restore_drill/blobs. Never share roots across DBs.
3. Keep destination **offline**, even if restore reports failure: pg_restore may have
   committed before a later failure. Inspect the destination and its stop state.
   Only a specifically identified disposable failed drill DB may be recreated.
4. Prepare a new private connection directory for that destination with the existing
   owner secret, never overwrite the active connection. Use `--root PATH` for store
   commands and `--storage PATH --blobs PATH` for control commands. Reapply **current**
   suppressions from the separately maintained register, run expiry/collect/verify,
   confirm all historical jobs cancelled and global stop true, compare expected
   retained source/derivation counts and the original source digests.
5. Provision new destination service accounts, validate readiness and guarded reads,
   and review independent worker/schedule/output/backup copies. Restore does not switch
   the active deployment and does not restore credential files or reset boot counters.
6. For an actual recovery, explicitly change launch paths after that verification;
   reopening permits only future work. For a drill, dispose only its named test DB,
   temporary service roles and blob root. Preserve the original DB, volume and secret.

Acceptance uses isolated temporary DBs/roles/blobs and generated secrets; no owner
reset or Internet target traffic. `tests/test_operations.py` tests load/backpressure,
readiness failure/recovery, non-mutating state counts, low disk, role denials and
source-bound inspection/delivery, token replacement, retention and stopped restore
with current suppression reapplication. Existing two-worker HTTP/TLS, lost-ACK,
kill/restart, heartbeat, retention, migration and browser drills remain in full
`make check-db`. The production-browser test serves the actual built assets and API
on one origin using the restricted read role, checks readiness/dashboard/search,
zero external requests and Axe. This is operational acceptance, not Phase 13 capacity
or precision/recall evaluation.
