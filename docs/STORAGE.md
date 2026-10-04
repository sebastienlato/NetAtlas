# Durable observation pipeline — through Phase 6

Package 0.5.0 adds a local PostgreSQL 18.3 / SQLAlchemy / Alembic adapter, private
content-addressed evidence, immutable history, current-service projections and a
transactional outbox. Package 0.6.0 adds PostGIS 3.6.4, independent enrichment and
gazetteer snapshots (migration 0003). **Only synthetic ingestion is enabled.** Phase 7 adds local metadata read routes; no
upload route, worker daemon or stored-data UI is implemented.
Phase 6 adds a bounded local search adapter; see [SEARCH.md](SEARCH.md).
The collector and offline derivation engine do not import storage.

## Local setup and checks

Install a Docker-compatible engine and Compose. On the verified macOS host:

```sh
brew install colima docker docker-compose
colima start --profile netatlas --cpu 2 --memory 2 --disk 12 --vm-type vz
make db-up COMPOSE=docker-compose
make db-migrate
make check-db COMPOSE=docker-compose
```

Colima may round the requested disk up; this host received a 20 GiB data disk.
Docker Desktop / Linux with the Compose plugin uses `make db-up` and `make check-db`
without the override. Runtime pins from earlier phases are unchanged. `make check`
alone runs offline/loopback tests and reports database tests skipped unless
`NETATLAS_TEST_DB=1` is set. `make check-db` starts Compose and runs **the full
make check with real database tests enabled**. CI uses that command; no silent
SQLite substitute or network scanning. Tests create/drop randomly named synthetic
databases and use temporary blobs. Backup tests use Compose's matching pg_dump and
pg_restore clients. TLS tests still require the local OpenSSL executable.

`init-local` creates mode-0600 random `data/storage/postgres-password` and private
`connection.json` (host, port, database; no credential printed). Compose mounts the
password as a secret, publishes only `127.0.0.1:55432`, and uses a named PostgreSQL
volume. The PostgreSQL base is pinned by version **and multi-platform digest** in
`docker/Dockerfile.postgis`; PostGIS server/scripts packages are pinned to
`3.6.4+dfsg-2.pgdg13+1`. Compose builds this image natively for arm64/amd64.
`db-up` includes `--build`; APT transitive OS packages can change, so this is not a
bit-for-bit image reproduction guarantee. Missing pinned packages fail closed.
Connections require SCRAM passwords. The DB owner account is for trusted local
operators/tests only; it is not an application/public role. PostgreSQL's local socket
inside the container is trusted for operator backup commands. Container/OS admins
can read all data; this is not multi-tenant isolation. Do not expose the port.

```sh
make db-down                     # stop, keep volume
# With standalone Compose:
make db-down COMPOSE=docker-compose
```

Do not delete the named volume or local secret to restart. Password changes require
coordinated DB credential rotation; replacing the file alone does not rotate an
initialized server. Data, blobs, secrets, backups, restored copies, and test output
belong under ignored data/ or temporary test directories, never Git.

## Synthetic smoke and operator commands

This creates a **new synthetic fixture**, not a measurement:

```sh
umask 077
uv run --locked python - <<'PY'
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from netatlas.config import Settings
from netatlas.examples import example_observation
from netatlas.observation import Observation
now = datetime.now(UTC)
row = Observation.model_validate(example_observation(Settings()).model_dump() | {
    'observation_id': uuid4(), 'started_at': now, 'finished_at': now,
})
Path('data/storage/synthetic.jsonl').write_text(row.model_dump_json() + '\n')
print(row.observation_id)
PY
uv run --locked netatlas-store ingest --input data/storage/synthetic.jsonl --synthetic
uv run --locked netatlas-store ingest --input data/storage/synthetic.jsonl --synthetic
uv run --locked netatlas-store derive --id OBSERVATION_UUID
uv run --locked netatlas-store verify
uv run --locked netatlas-store consume
uv run --locked netatlas-store expire
uv run --locked netatlas-store collect
```

Replace OBSERVATION_UUID with the printed synthetic UUID. `derive --pack PATH`
selects a bounded Phase 3 pack; otherwise it uses the bundled core. It reconstructs
the immutable source and computes the result locally; it does not trust an uploaded
derivation. Multiple pack/engine/taxonomy identities coexist. `verify` reconstructs
and hashes every retained source and fully recomputes every derivation. Run expiry
first if records have aged out. No raw evidence is printed. No captured URLs are
opened. Synthetic address bounds are TEST-NET-1/2/3, 2001:db8::/32, 127.0.0.1 and ::1.
The flag and address checks cannot prove a payload is fictional: operators must
supply authored fixtures only. Arbitrary Internet/private-address inputs fail closed.

## Identity, transaction and acknowledgement

Ingest accepts explicit observation v1/v2, with unchanged canonical serialization
from Phase 3: validated defaults, sorted keys, compact ASCII JSON, ordered arrays.
A UUID plus canonical SHA-256 identifies an immutable source. Exact replay returns
`replayed`; the same UUID with different canonical content fails without a write.
Distinct UUIDs always preserve separate measurement history even if bytes match.
The original schema, envelope fields, timestamps and source/pack provenance survive.

One row is one transaction and acknowledgement, **not one entire JSONL file**.
The existing bounded file reader enforces 16 MiB / 1024 rows / 1 MiB per row,
32-level nesting and duplicate-key rejection. Processing stops at the first invalid
row. Each prior successful row has a flushed acknowledgement containing only UUID
and status. Fix the input and replay the file; never infer failure of prior committed
rows from a later error or lost connection. There is no payload-copying dead-letter
queue: operators retain the private original file and inspect it locally.

Within a PostgreSQL advisory transaction lock, ingestion:

1. Validates bounds, synthetic policy, timestamps, suppression and existing identity.
2. Extracts all response and certificate base64 bytes to SHA-256 files, mode 0600
   under a 0700 directory. Files are fsynced, linked atomically, and the directory
   fsynced. Existing blobs are read and hash-checked, never overwritten.
3. Inserts the envelope JSONB with base64 fields replaced by digests, exact JSON-pointer
   references, typed endpoint/time/outcome columns, and blob catalog entries.
4. Rebuilds that endpoint's current projection and inserts the outbox event in the
   same transaction. PostgreSQL commits with `synchronous_commit=on`.
5. Only then acknowledges. A lost acknowledgement is safe to replay. Replays also
   reconstruct and verify source/blob integrity; missing bytes are never acknowledged.

Reconstruction restores base64 from the references, validates v1/v2, then compares
the original canonical digest. Stored JSONB with digest placeholders is an internal
storage representation, **not a new observation wire schema**. Metadata can contain
peer assertions and remains private. Raw bytes are not duplicated in the DB.
SHA-256 content equality saves bytes, not history. Checksum equality is not trust.

Rollback/crash after publication may leave orphan blobs. `collect` holds the same
pipeline lock, removes unreferenced hashes/staging files, and fsyncs the directory.
Retention first commits source deletion; only then removes unreferenced files in
a separate locked transaction. A crash between them leaves harmless private orphans
that the next collect removes. Shared blobs remain while any observation refers to
them. Missing/corrupt live files require verified backup recovery; collect never
invents them. Durability assumes PostgreSQL and the filesystem honor fsync, their
storage is intact, and all writers/maintenance use this protocol. No simulated
physical power-cut/storage-controller qualification has been performed.

The single local lock deliberately serializes ingestion, derivation, consumers,
maintenance, backup and reads. Lock wait is capped at 10 seconds and statements at
60 seconds. This is a correctness baseline, not distributed throughput architecture.
Do not use two databases with the same blob root. No automatic retries or deadlock
hiding; a failed operation can be explicitly replayed.

## Schema and current-view ordering

Alembic 0001 creates `observations`, `evidence_refs`, `blobs`, `packs`, `derivations`,
`current_services`, `outbox`, `consumer_receipts`, `consumer_observations` and history
UPDATE-rejection triggers. 0002 transactionally backfills 30-day source expiry and
adds `suppressions` and 90-day `tombstones`. Tests upgrade a populated 0001 and verify
original JSON plus expiry and restored immutability. 0003 adds PostGIS and enrichment
without rewriting original rows; populated Phase 4 and spatial Phase 5 restores are
tested. See [ENRICHMENT.md](ENRICHMENT.md) for schema and offline demonstration.
Migrations are packaged with
the wheel. Downgrades intentionally fail; restore a tested backup instead.

Endpoint key is `(canonical address, transport, port)`. Current pointers independently
select maximum `(finished_at, started_at, UUID)` using PostgreSQL's timestamp/UUID
ordering, independent of input/arrival order:

- `last_attempt`: every outcome, including error/timeout/refusal.
- `last_open`: TCP-open, even with no response bytes.
- `last_evidence`: nonempty response or certificate bytes. This is a successful
  capture, not proof of a valid protocol, honest banner, physical identity or uptime.

Negative or empty attempts never erase prior evidence. When history expires or is
removed, projections are rebuilt from remaining observations; an empty endpoint
vanishes. A UUID tiebreak has no physical chronology meaning. Receipt time is separate
operational metadata. Records older than 30 days or over 5 minutes in the future
are rejected rather than extending retention because they arrived late.

Derivation IDs hash the full deterministic derived record; a unique key also covers
source ID/digest, pack digest, engine and taxonomy. Unexpected different output for
the same identity fails (requires engine-version review). Packs are retained as
canonical JSONB snapshots; hashes distinguish same-version content edits. Sources,
evidence selectors/hashes and all Phase 3 uncertainty semantics remain traceable.

## Outbox delivery and replay

Observation/derivation inserts and removal transactions append events containing
only sequence ID, source UUID, kind and operational timestamp. Exact replays create
no second event. `consume` calls a DB handler and writes its per-consumer receipt
**in the same transaction**. A failure before receipt/commit rolls both back; a lost
post-commit acknowledgement finds the receipt on retry. Concurrent workers serialize.
This guarantees atomic effects only for handlers using the provided DB connection;
external side effects require their own idempotency and are not implemented.

The supplied consumer mirrors source UUID/digest into a private table. It reads
current authoritative state and refuses expired sources, so old/reordered events
cannot resurrect removed observations. Cascading deletion immediately removes its
rows even while the consumer is stopped. A different bounded consumer name has
independent receipts. To replay history, use `consume --replay --limit 100 --after 0`,
then supply each returned cursor as `--after` until delivered is zero. Ordinary
consumption needs no cursor and skips receipts. Replay deliberately calls handlers
again; they must be idempotent. No FIFO external broker, lease or search index exists.

Events/receipts for removed observations expire after 90 days during maintenance;
live-source events remain while that source exists. This defines the local replay
horizon. A future external projection must coordinate deletion acknowledgements
and retention before adopting this outbox; no arbitrary external consumer guarantee
is implied by the local demonstration.

## Minimization, private access, retention and opt-outs

- **No real-data ingestion is authorized or enabled.** Keep bounded collection,
  authored synthetic inputs and separate credentials. Never use captured tokens.
- Evidence stays private; only counts, UUIDs/digests and generic diagnostics cross the
  operator CLI output boundary. There is no raw-content display/export/API and no
  automatic partial redaction that would silently change canonical source evidence.
  Product/HTTP/SSH metadata, pack labels and hashes also remain sensitive.
- The removal policy for sensitive evidence is whole-observation deletion, including
  its derived rows, references and projections, followed by unreferenced blob cleanup.
  If later public display requires field-level redaction, create a separately versioned
  sanitized projection and audit it before enabling real inputs; never rewrite history
  and pretend it is the original measurement.
- Stored observations expire at `finished_at + 30 days`; reads/derivations reject
  expired records immediately. Run `expire` at session start, at least daily while
  storing data, and before backup/restore use; there is no background scheduler.
  Physical deletion is maintenance-driven; expiry alone is not secure file erasure.
  The authoritative current pointer table is private and is refreshed by maintenance.
- `netatlas-store suppress --network 192.0.2.0/24` persists an indefinite CIDR denial,
  deletes all matching observations and descendants, rebuilds affected current rows,
  emits deletion events and runs GC. Suppressions take precedence over replay. Keep
  the suppression register separately for restoring old backups. The CLI provides no
  unsuppress command. Minimal UUID/digest tombstones last 90 days and reject removed
  identities even if their envelope/address is changed.
- Stored-data suppression does **not** hot-update active measurement. Stop campaigns,
  add the same CIDR to measurement `opt_out_cidrs`, preview before restart, and remove
  matching private spools/offline derivations/backups separately. Discovery spool and
  fingerprint outputs have independent ownership; the DB cannot find every copy.
- Backups must be private and limited to 7 days, or shorter on a removal request.
  Remove affected backup copies immediately or quarantine them and reapply current
  suppression policy before use. Account for replicas, snapshots and SSD behavior;
  deleting a path does not establish forensic erasure. Encryption, remote access,
  separate least-privilege service roles, automatic retention jobs and production
  key management remain operational hardening work before any real ingestion.

## Backup and restore drill

Stop other operator commands during a manual drill. The backup adapter takes the
pipeline lock across PostgreSQL pg_dump and a verified copy of all referenced blobs.
It checks that the Compose server matches the configured database connection,
fsyncs a private staged directory, includes a manifest with archive/blob hashes,
and publishes a new directory. This includes migrations, history, current pointers,
packs, derivations, suppression state, outbox and consumer receipts. Credentials are
not included. Trusted operator archives only: SQL dumps are executable input, not a
format accepted from peers or public uploads.

```sh
uv run --locked netatlas-store expire
uv run --locked netatlas-store backup --output data/storage/backups/drill-1
# Use docker-compose instead of docker compose on the standalone Homebrew setup.
docker compose exec -T db createdb -U postgres netatlas_restore_drill
uv run --locked netatlas-store restore --input data/storage/backups/drill-1 --database netatlas_restore_drill
```

Restore requires a separately created **empty** `netatlas_restore_*` database, verifies
the archive and each copied blob, uses pg_restore's single transaction, applies newer migrations, expires old
rows, then reconstructs sources and replays derivations. It writes a separate blob
root `data/storage/netatlas_restore_drill/blobs`; it does not switch the active DB.
If restore is interrupted, inspect the destination and verify it; do not assume a
failed acknowledgement means pg_restore did not commit. Discard/recreate only the
explicit disposable restore database when retrying a drill. Apply any newer opt-outs
before promoting a restored copy. A manifest verifies corruption, not authorship.

The integration test automatically exercises the dump/restore workflow in isolated
synthetic databases, checking observations, blobs, derivations, duplicate replay,
and a partially consumed outbox. The manual CLI commands are also exercised locally.
No remote backups, PITR/WAL archiving, failover, encryption, distributed storage,
Internet dataset or production recovery-time objective is claimed.

References: [PostgreSQL synchronous commit](https://www.postgresql.org/docs/18/runtime-config-wal.html),
[pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html),
[pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html),
[Alembic shared connections](https://alembic.sqlalchemy.org/en/latest/cookbook.html#sharing-a-connection-across-one-or-more-programmatic-migration-commands),
[Compose secrets](https://docs.docker.com/reference/compose-file/secrets/).

## Phase 5 upgrade and operational compatibility

Before replacing a Phase 4 container, take a locked backup with its existing matching
clients, then run `make db-up COMPOSE=docker-compose` and `make db-migrate`. Keep the
named volume and existing secret; this remains PostgreSQL 18.3 at the same data path.
The build context is restricted to `docker/`, so credentials/datasets are never sent
to the image builder. A fresh database gets PostGIS through migration 0003, not an
image init hook; existing databases follow exactly the same migration. Only the core
PostGIS extension is enabled, not raster, topology or geocoder extensions.

`netatlas-store enrich --id UUID --dataset PATH --sha256 FILE_SHA --at ISO_TIME`
computes a separate result from an unexpired source and a checksum-pinned local
bundle. It does not accept a supplied result. Source/dataset/result/outbox writes
share the existing lock and commit semantics. Results use the existing source-level
`derivation` event kind. `verify` now returns an additional `enrichments` count and
checks all stored points/boundaries against immutable snapshots.

Backups include the extension declaration and spatial tables; restore needs the
PostGIS packages installed. Empty means no user tables, including no preinitialized
spatial_ref_sys. The custom image deliberately adds no PostGIS template/init hook.
Older Phase 4 backups are migrated before maintenance/replay. Source deletion removes
enrichment rows; unused snapshots and their gazetteer projections are collected in
that removal transaction. Independently downloaded datasets and offline outputs,
including the demo subset, are outside DB retention and require separate handling.

## Phase 6 search compatibility

Package 0.7.0 migration 0004 adds nine indexes to the existing immutable tables;
no source/schema rewrite or new search projection is needed. `make db-migrate`
upgrades the existing database without changing credentials/volume. The local
`netatlas-search` command requires no blobs and returns private bounded metadata
with exact counts; no public display or real-data authorization is added.

Queries share the pipeline advisory lock, check actual retention/suppressions and
select exact derivation identities. Index rebuilds use REINDEX under that same lock;
source deletion transactionally updates every index. Read [SEARCH.md](SEARCH.md)
for clock, current/history, unknown and aggregation semantics. New tests compare
search results across populated 0003 upgrades, Phase 5/6 archives and REINDEX; older
0001/0002 upgrade and Phase 4 restore coverage remains. Restore applies 0004 before
verification. Output files need separate retention handling.

## Phase 7 read compatibility

The bounded local HTTP adapter now exposes synthetic search metadata and a guarded
gazetteer, using the existing database/lock and migrations through 0004. No schema,
volume, secret, raw blob, retention or ingestion-policy change is needed. Requests
never reconstruct sources, mutate data or execute collection. DB-owner access is
still local and trusted, not a production read-only role. See [API.md](API.md).
