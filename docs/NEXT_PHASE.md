# PHASE 4 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
The opened NetAtlas folder is the repository root. Complete exactly Phase 4 in this
fresh Work chat; do not begin Phase 5.

First read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md,
DECISIONS.md, CONTRIBUTING.md, SECURITY.md, docs/DATA_MODEL.md, docs/DISCOVERY.md,
docs/PROTOCOL_EVIDENCE.md and docs/FINGERPRINTS.md. Inspect Git status/remotes,
toolchains, code and tests. Repository files are authoritative. Respect existing
user changes and make routine engineering decisions without approval gates.

Phase 3 delivered package 0.4.0 on Python 3.14/uv/FastAPI/Pydantic with a React/
TypeScript/Vite shell. Config is v3; observations/manifests v2, with explicit v1
observation compatibility. Rule-pack and derivation schemas are v1, engine is
fingerprints-1 and taxonomy is netatlas-categories-1. No durable storage exists yet.

Discovery remains bounded literal IPv4/IPv6 and small CIDRs with pinned policy,
exclusions/opt-outs, shared global/per-prefix pacing, queue/concurrency/deadlines,
cancellation and private ignored JSONL/manifests. CLI defaults dry-run; measurement
needs enabled operator identity and --measure. Protocol capture separately requires
measurement.protocol_evidence = true. Lab mode permits only literal 127.0.0.1/::1.
API/UI cannot initiate measurement. No Internet campaign has been run.

HTTP/TLS/SSH/SMTP collection uses at most two admitted connections, two GET / requests
and one TLS handshake per endpoint, with cumulative wire/retention budgets. No DNS,
SNI, named Host, redirects, cookies, authentication, mail, STARTTLS or active device
commands. TCP reachability is distinct from protocol outcome. Raw base64 evidence
and metadata are hostile peer assertions; TLS certificate verification is not performed.

Phase 3 adds separate deterministic offline derivations with source UUID/schema/
digest, pack ID/version/digest, engine/taxonomy version and precise decoded-byte
selectors/hashes. The core pack has four literal rules for nginx, OpenSSH and Postfix
assertions. Confidence is ordinal asserted/corroborated, never calibrated probability
or identity proof. Preserve unknowns and multiple candidates; broader device classes
have fictional test coverage only. Raw observations are never rewritten. Shared
protocol_syntax.py is I/O-free; collectors and derivations remain separate.

Offline fingerprint apply/inspect/replay is bounded to regular files: 128 KiB pack,
64 rules with four conditions, 16 MiB input/1024 rows, 1 MiB line, 32-level nesting,
8192-byte body window, 128 candidates/record, 32 MiB output. Outputs are private,
atomic and no-clobber under data/. No executable rules, arbitrary regex, active
content, networking or raw-content logging. Deterministic records omit a processing
clock; operational run timestamps may be separate. Preserve source/pack snapshots
and engine version for replay. Existing embedded fingerprint shapes are placeholders.

Phase 3 validation passed make check: 130 Python and 3 web tests plus lint, strict
types, builds and offline smoke; all 130 Python tests also passed with warnings as
errors. There are 63 fingerprint tests and 47 labeled synthetic corpus cases.
An existing TLS fixture accept/close race was fixed without changing production
collectors or suppressing warnings. Verify results yourself. TLS tests need OpenSSL
and generate temporary keys/certificates. Runtime pins remain Python 3.14.7,
uv 0.12.19, Node 26.8.1 and npm 11.19.0. No new Phase 3 dependency was added.

Implement Phase 4 — Durable Observation Pipeline: PostgreSQL schema/migrations,
ingestion, content-addressed blobs, immutable observation/derivation history,
current-service projections, deduplication, transactional outbox and local Compose
setup. Follow ADR-005's PostgreSQL/SQLAlchemy/Alembic direction; inspect available
container/database tooling before deciding local setup. No search cluster is needed.
Do not implement geographic enrichment or search infrastructure in this phase.

Define durable ingestion identity, acknowledgement and transaction boundaries.
Observation UUID plus canonical content must distinguish exact replay from a
same-ID/different-content conflict; blob content equality must never erase distinct
measurement history. Preserve explicit v1/v2 compatibility and independent derivation
versions. Keep source evidence, pack provenance and derived references traceable.
Handle duplicate/reordered inputs, stale arrivals and negative attempts without
losing last successful service evidence; define deterministic current-view ordering.
Design recoverable blob/database publication and orphan cleanup without acknowledging
non-durable data. Add a replayable outbox with idempotent consumers and tested failure
boundaries. Keep scanner, domain, derivations, storage and API separable.

Acceptance includes duplicate/reordered input, transaction failure/replay, upgrade
migration, basic backup/restore and retention tests. Document/run reproducible local
Compose commands and meaningful database integration tests. Use synthetic fixtures
only; keep databases, datasets, blobs, observations, local config, credentials and
generated outputs out of Git. Establish minimization/redaction, private access,
retention expiry and opt-out/removal semantics for stored evidence and projections
before any real-data ingestion; no real-data ingestion is authorized by this task.
Do not add public upload/measurement controls or claim later API/search/UI work exists.

Never add credential guessing, authentication bypass, exploitation, persistence on
remote targets, remote modification or destructive device actions. Do not enlarge
probe coverage or traffic budgets to fill storage/fingerprint gaps. No public-target
smoke tests, commercial discovery databases, mandatory paid services, releases or tags.
Ask only for genuine blockers, credentials, permissions or unavoidable manual actions
after completing independent authorized work; do not introduce routine approval gates.

At completion run relevant checks and make check; update authoritative docs with
actual results, limitations and state; replace docs/NEXT_PHASE.md with a self-contained
Phase 5 kickoff. Review tracked files/diff for secrets, captures and generated data;
commit with a Phase 4 message; push; verify local HEAD equals the remote delivery
branch and the working tree is clean. Report delivery, checks/results, commit hash,
push/CI status, blockers and exact current state. Include the complete Phase 5 kickoff,
then stop.
