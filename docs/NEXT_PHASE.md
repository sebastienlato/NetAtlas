# PHASE 5 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
Complete exactly Phase 5 in this fresh Work chat; do not begin Phase 6.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md, SECURITY.md, docs/DATA_MODEL.md, docs/STORAGE.md,
docs/DISCOVERY.md, docs/PROTOCOL_EVIDENCE.md and docs/FINGERPRINTS.md first. Inspect
Git status/remotes, toolchains, code and tests. Repository files are authoritative.
Respect user changes; make routine engineering decisions without approval gates.

Phase 4 delivered package 0.5.0 on Python 3.14/FastAPI/Pydantic with a React/TypeScript/
Vite shell. Config is v3; observations/manifests v2 with explicit v1 reads;
rule-pack/derivation schemas v1; engine fingerprints-1; taxonomy netatlas-categories-1.
Storage uses PostgreSQL 18.3, SQLAlchemy, psycopg and packaged Alembic head 0002.

Discovery remains bounded literal IPv4/IPv6 and small CIDRs with pinned policy,
exclusions/opt-outs, shared pacing, queue/deadlines/cancellation and private spool.
CLI defaults dry-run; enabled operator identity and --measure are required.
Protocol capture additionally requires measurement.protocol_evidence = true.
Lab mode permits only literal 127.0.0.1/::1. At most two connections, two GET / requests
and one TLS handshake per endpoint. No DNS/SNI, redirects, cookies, authentication,
mail, STARTTLS or active device commands. No Internet campaign has been run.

Fingerprint derivations are pure, independent and deterministic, with source/pack
hashes, engine/taxonomy versions and exact decoded-byte selectors/hashes. The core
pack has four nginx/OpenSSH/Postfix assertion rules; other device classes have
fictional test coverage only. Preserve unknowns/multiple candidates. Confidence is
ordinal asserted/corroborated, never identity proof or calibrated probability.

The local netatlas-store CLI accepts authored synthetic documentation/loopback
fixtures only. UUID plus canonical digest distinguishes replay from conflict.
Distinct measurement history survives blob deduplication. Private raw byte files
are fsynced before synchronous DB commit; acknowledgements follow each row's commit.
Internal JSONB hash placeholders plus evidence_refs reconstruct original v1/v2
sources. Immutable history, pack snapshots and independent derivations are verified
by replay. Preserve wire compatibility, evidence and provenance.

Current pointers independently select last attempt/open/nonempty evidence using
(finished_at, started_at, UUID). Negative/stale/empty arrivals preserve prior evidence.
A shared local advisory lock coordinates pipeline operations and GC. Transactional
outbox plus same-DB idempotent consumers/receipts supports cursor replay; no external
consumer, distributed lease, search service or read API is implemented.

Sources expire after 30 days; reads reject expiry and explicit maintenance deletes
history/projections/unreferenced blobs. Persistent CIDR suppression blocks ingestion
and removes matching records. Minimal tombstones/removed-source events last 90 days.
Spools/offline outputs/backups require separate removal. Backup policy is 7 days;
old restores require current suppressions before use. No real-data ingestion is
authorized. No public raw display, field-level sanitizer, encryption or production
service-role isolation exists. See STORAGE for precise access and recovery limits.

Runtime pins: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0. TLS tests require
OpenSSL and temporary keys. Local Homebrew setup has Docker/standalone Compose and
a dedicated Colima netatlas profile; inspect current availability. Start with
make db-up COMPOSE=docker-compose, then make db-migrate. Docker Compose plugin hosts
omit the override. make check-db runs the full make check with PostgreSQL enabled;
plain make check skips DB tests without NETATLAS_TEST_DB=1. CI requires check-db.
Phase 4 passed 171 Python / 3 web tests, lint/types/builds/offline smoke, migration
upgrade, transaction/replay/retention and database/blob backup/restore drills.
Verify current results; do not treat these historical counts as fresh validation.

Implement Phase 5 — Network and Geographic Enrichment: versioned offline ASN/prefix
and approximate-city lookup, place gazetteer, PostGIS points/boundaries and attribution
metadata. Use separate versioned derivations, never rewrite raw observations.
Inspect available free datasets and their exact license/redistribution/attribution
terms before choosing a small freely usable demonstration dataset. Keep downloaded
datasets and generated outputs out of Git; commit only small authored synthetic
fixtures or explicitly licensed material appropriate to the repository. No mandatory
paid service or credentials-dependent data source. Never infer precise person/device
location from IP geography or claim exhaustive coverage.

Acceptance covers unknowns, IPv4/IPv6 longest-prefix matching, invalid/stale datasets,
source/version/checksum reproducibility, location uncertainty, antimeridian handling,
and same-name place disambiguation. Add a reviewed PostGIS migration and reproducible
local Compose setup, preserving storage/restore compatibility and retention/removal.
Show a small offline enrichment demonstration and meaningful database integration
tests. Keep collector, domain, enrichment, storage and API separable. Do not implement
Phase 6 search infrastructure, later query API or geographic UI.

Never add credential guessing, authentication bypass, exploitation, remote
persistence/modification or destructive actions. Do not enlarge probe coverage or
budgets to fill enrichment gaps. No public-target smoke tests, commercial discovery
databases, releases or tags. Ask only for genuine blockers, credentials, permissions
or unavoidable manual actions after completing independent authorized work.

At completion run relevant checks and make check with DB integration enabled; update
authoritative docs with actual state, results and limitations; replace NEXT_PHASE
with a self-contained Phase 6 kickoff. Review tracked files/diff for secrets, captures
and generated data; commit with a Phase 5 message; push; verify local HEAD equals
remote delivery HEAD and the tree is clean. Report checks, commit, push/CI, blockers,
exact current state and the complete Phase 6 kickoff, then stop.
