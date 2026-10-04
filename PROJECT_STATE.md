# Project state

Updated: 2026-10-04. **Phase 1 — Bounded Discovery Engine is complete.**
Phase 2 has not started. Package version: **0.2.0**; configuration version: **2**.

## Delivered

- Modular asyncio TCP connect discovery with literal IPv4/IPv6 addresses and small
  strict CIDRs, streaming seeded expansion, overlap/port deduplication, eligibility
  preview, exclusion/opt-out denials and optional restrictive allowlists.
- Conservative pinned IANA-derived special-use policy plus runtime classification;
  explicit lab mode accepts only literal `127.0.0.1` and `::1`, up to 16 ports.
- Shared no-burst global and /24 IPv4, /48 IPv6 pacing, bounded queue/concurrency,
  connect and campaign deadlines, SIGINT/SIGTERM/task cancellation, socket cleanup.
- Dry-run CLI default; dialing requires both `--measure` and enabled configuration
  with syntactically validated operator name/contact and research user-agent.
- Version-1 JSONL observations and atomic version-1 campaign manifests under ignored
  `data/<campaign UUID>/`, configuration/policy hashes, runtime/scanner identity,
  seed/order, outcome counts, incomplete attempts and output checksum. Redacted JSON logs.
- Phase 0 API/domain/web foundation retained. API health reports phase 1 but never
  enables measurement in the API; the UI honestly remains a preview without scan controls.

## Architecture now

Python 3.14/asyncio/FastAPI/Pydantic and React/TypeScript/Vite. Domain models have no
I/O. `discovery/` separates scope, policy, pacing, TCP sockets, campaign coordination
and local spool. No protocol collectors, identification engine, database, ingestion
pipeline, search index, geolocation dataset, map engine, or Internet campaign has
been implemented or run. PostgreSQL/PostGIS, optional OpenSearch and MapLibre remain planned.

## Commands and validation

`make setup`, `make check`, `make dev-api`, `make dev-web`; see README and
`docs/DISCOVERY.md` for offline previews and explicit loopback operation.

- `make check`: passed; 28 Python tests and 3 web tests; Ruff lint/format, strict mypy,
  Biome, TypeScript, Python wheel/source build, Vite production build, offline CLI
  config/example/schema/discovery smoke checks.
- Tests cover registry/address boundaries and deny precedence, huge-scope rejection,
  deterministic streaming/deduplication, identity/limits, IPv4/IPv6 loopback open and
  refused connections with peer EOF, injected timeout/errors, socket closure,
  shared rate/concurrency/queue bounds, deadline/event/task/repeated cancellation,
  subprocess SIGTERM, failure cleanup, spool exclusion, JSONL/manifest checksums,
  and log redaction. Only synthetic or loopback fixtures; no Internet targets dialed.
- Locked dependencies unchanged except the local package version. Runtime inspection:
  Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0; no new service dependency.
- Private GitHub repository: https://github.com/sebastienlato/NetAtlas; delivery branch
  `main`. Quality CI runs `make setup` and `make check` on Linux. Git history and
  Actions are authoritative for the final commit and its CI status.
- Verify delivery with `git rev-parse HEAD`, `git ls-remote origin refs/heads/main`,
  and `git status --porcelain`: hashes must match and the working tree must be clean.

## Limitations and blockers

No current implementation blocker. TCP connect success means reachability only;
`closed` with `connection_refused` means an explicit refusal, and timeout is ambiguous.
No application bytes, user-agent, or protocol requests are sent. Identity validation
checks syntax, not ownership. Real campaign operator/contact and institutional/network
permissions remain separate prerequisites, not implied by implementation.

Budgets cover one local campaign's concurrent tasks; an advisory spool lock prevents
simultaneous runs sharing `data/`. This is not host-wide or distributed coordination.
No live routing dataset, hot policy reload, fairness guarantee, retry, resume, or
crash-recovery ingestion exists. IANA rules are deliberately over-restrictive and
require reviewed updates. Graceful stops flush/fsync; hard kill/power loss may leave
an unfinished manifest or partial last line. See `docs/DISCOVERY.md` for exact caps.
API/UI are unauthenticated loopback development components. Docker is unnecessary
until the database phase. Public licensing and deployment remain owner decisions.

## Next

**Phase 2 — Protocol Evidence**, in a fresh chat using `docs/NEXT_PHASE.md`.
Do not begin it in the Phase 1 chat. Repository files hold the complete handoff.
