# Project state

Updated: 2026-10-04. **Phase 4 — Durable Observation Pipeline is complete.**
Phase 5 has not started. Package **0.5.0**; config **3**; observation/manifest **2**;
rule-pack/derivation schemas **1**; engine **fingerprints-1**;
taxonomy **netatlas-categories-1**; Alembic head **0002**.

## Delivered

- Bounded literal IPv4/IPv6 discovery, pinned policy, exclusions/opt-outs, narrow
  loopback lab mode, shared pacing/queue/deadlines/cancellation and private spool.
- Opt-in HTTP/TLS/SSH/SMTP evidence within two connections, two GET / requests and
  one TLS handshake per endpoint. No DNS/SNI, redirects, cookies, authentication,
  mail, STARTTLS, crawling or state-changing interactions. TCP-open is distinct
  from protocol success; TLS certificate verification is not performed.
- Pure offline deterministic fingerprints, bounded declarative packs, separate
  source/pack/engine/taxonomy provenance and precise decoded-byte selectors/hashes.
  Core pack 1.0.0 has four nginx/OpenSSH/Postfix assertion rules. Broader categories
  have fictional test coverage only. Unknowns and multiple candidates are preserved.
- Phase 4 PostgreSQL 18.3 / SQLAlchemy / psycopg / Alembic storage package, two
  packaged migrations, private content-addressed raw response/certificate blobs,
  immutable v1/v2 observation and independent pack/derivation history.
- `netatlas-store` local operator CLI: initialize/migrate, bounded synthetic ingest,
  derive/verify, consume/replay, expiry/suppression/GC and backup/restore. No public
  ingestion route, uploaded derivation trust or measurement controls added.
- UUID plus canonical digest distinguishes exact replay from identity conflict.
  Equal content shares files without deleting distinct measurement history.
  Fsynced files precede synchronous DB commit; row acknowledgements follow commit.
  Partial input files may have committed rows; replay is the recovery contract.
- Separate current pointers for last attempt, TCP-open and nonempty evidence by
  `(finished_at, started_at, UUID)`. Negative/stale/empty attempts preserve evidence.
- Transactional outbox and idempotent same-DB consumer with atomic effects/receipts,
  separate consumer identities and cursor-based replay. Old events read live truth
  and cannot restore deleted source rows. No external broker/index/consumer service.
- 30-day source expiry, private local owner access, whole-record removal, durable
  CIDR suppression, 90-day replay tombstones/removed-source event metadata, and
  documented spool/backup removal policy. Real-data ingestion stays prohibited.
- Version/digest-pinned Compose DB, generated private credentials, loopback-only
  published port, consistent locked DB/blob backups and empty-database restore with
  source/derivation verification. Backup tools verify the Compose server matches
  the configured connection. No search/geographic service is deployed.
- API health and web shell describe Phase 4; they still show no stored observations
  and cannot start measurement. Existing examples remain authored synthetic data.

## Architecture now

`domain.py`, `evidence.py`, `observation.py` are I/O-free contracts. `discovery/`
owns policy/campaign orchestration; `collectors/` acquires bounded protocol bytes.
`derivations/engine.py` is pure, with bounded file I/O in `offline.py`. Shared syntax
parsers remain independent from collection and storage execution.

`storage/` depends on these contracts and offline readers; measurement/API do not
import it. PostgreSQL stores typed endpoint/time/outcome and private envelope JSONB
with hash placeholders. `evidence_refs` restores exact original base64 fields for
canonical verification. This internal representation does not change wire schemas.
Pack/result snapshots remain separate. One advisory lock coordinates local pipeline
transactions and filesystem maintenance; no distributed-throughput claim.

No PostGIS, ASN/geography enrichment, search cluster, stored-data query API, geographic
UI, distributed workers, real Internet dataset, release or tag exists. No Internet
campaign was run. Phase 5 is the next bounded increment.

## Commands and verified validation

See README and `docs/STORAGE.md` for setup, all operator commands, exact guarantees,
limits and reproducible Compose/restore drills. `make check` without the DB flag
explicitly skips DB tests; **`make check-db` runs the entire check with DB tests**.
Homebrew standalone Compose: `make check-db COMPOSE=docker-compose`.

- Full Phase 4 `make check-db COMPOSE=docker-compose` passes **171 Python tests and
  3 web tests**, Ruff/format, strict mypy, Biome/TypeScript, Python wheel/source and
  Vite builds, plus offline CLI smoke. This invokes the required `make check`.
- Storage acceptance contributes **41 tests**, including real PostgreSQL transaction
  rollback/lost acknowledgement, duplicate/concurrent/reordered inputs, blob dedup,
  v1/v2 and TLS evidence reconstruction, changed pack versions, immutable UPDATE
  rejection, consumer rollback/receipt/replay, retention/shared blobs, suppression,
  removal crashes, fsync failure, malformed input and redacted partial-file CLI errors.
- Populated migration 0001 upgrades to 0002 without rewriting source JSON, including
  expiry backfill and idempotent re-upgrade. Full DB/blob dump/restore verifies
  source/derivation replay, preserved consumer progress and empty-target enforcement.
  Corrupt archive and wrong Compose server checks fail before publication.
- Manual documented local CLI drill: synthetic ingest/replay, stored derivation,
  verification, consumption, expiry/GC, backup and separate empty-DB restore passed.
  Only synthetic data/loopback fixtures were used; generated data/credentials remain
  ignored. No actual power-cut, failover or real-world precision/recall test claimed.
- A remaining intermittent pre-existing TLS fixture cleanup warning prompted an
  explicit owned accept-task/transport teardown; no production networking change or
  warning suppression. The full suite also passes with warnings treated as errors.
- Runtime pins unchanged: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0.
  New dependencies are locked SQLAlchemy 2.1.3, Alembic 1.20.0 and psycopg 3.3.6
  (plus their transitive packages). Docker/Compose/Colima setup is in ENVIRONMENT.
- CI now runs `make check-db` on Linux and removes its disposable Compose volume
  afterwards. Git history and Actions are final delivery/CI authority.

Private repository: https://github.com/sebastienlato/NetAtlas; delivery branch `main`.
Verify local HEAD against `git ls-remote origin refs/heads/main` and verify an empty
`git status --porcelain`. The phase completion report records the exact commit/CI.

## Limitations and blockers

No Phase 4 implementation blocker. Real ingestion is not authorized: only authored
synthetic inputs in documentation/loopback ranges pass policy. No real operator or
institutional network permission is implied. Credentials are generated for the local
DB only. OS/container admins and the DB owner are trusted. The API/web shell remains
an unauthenticated loopback development interface with no storage routes.

Raw evidence and typed metadata remain hostile/sensitive. No public preview or
field-level sanitizer exists. Removal deletes whole observations and dependent
records; retained evidence stays immutable. No encrypted backups, separate service
roles, public authentication or adversarial-local-account filesystem protection.
Before any later real ingestion, those operational/redaction requirements need an
explicitly authorized design. Measurement budgets and protocol gaps are unchanged.

Expiry and GC are explicit operator commands, not background jobs. Reads reject
expired sources; physical deletion/current-pointer refresh requires maintenance.
Keep backups at most 7 days; remove/quarantine affected copies on opt-out and reapply
newer suppression state after old-backup restoration. DB suppression does not alter
scanner opt-outs or delete existing spools/standalone derivation files. Follow STORAGE.

One global local lock favors correctness over throughput. Outbox atomicity covers
same-DB handlers only. Removal metadata has a 90-day replay horizon; external
projections need coordinated deletion semantics. No partitions, object storage,
PITR/WAL archiving, distributed leases, automatic restart/retry or production SLA.
Fsync durability assumes functioning storage/DB/OS; hardware failure can destroy data.

Source/pack hashes and ordinal asserted/corroborated confidence do not authenticate
identity, authorship, device type or vulnerability. Existing embedded fingerprints
remain placeholders. Canonical engine/schema versions must remain replayable.

## Next

**Phase 5 — Network and Geographic Enrichment**, in a fresh chat using
`docs/NEXT_PHASE.md`. Do not begin it in this Phase 4 chat.
