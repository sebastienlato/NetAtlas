# Project state

Updated: 2026-10-04. **Phase 0 — Foundation and Architecture is complete.**
Phase 1 has not started.

## Delivered

- Modular Python package with validated TOML settings, effective-config SHA-256,
  domain contracts, offline example/schema/config CLI, local FastAPI health/example
  endpoints and OpenAPI.
- React/TypeScript web foundation with API connectivity state and honest empty state.
- Python/web dependency management, runtime pins, meaningful smoke/contract tests,
  formatting/static checking/build commands, GitHub CI workflow.
- Architecture, decisions, complete 0–14 roadmap, contributor/security rules,
  environment/data-model records, and next-phase kickoff.

## Architecture now

Python asyncio/FastAPI/Pydantic and React/TypeScript/Vite. The domain layer has no
I/O; configuration defaults reject measurement enablement. There is **no scanner,
database, ingestion pipeline, search index, geolocation data, map engine, or live
measurement**. PostgreSQL/PostGIS, optional OpenSearch, and MapLibre are planned
components, not present infrastructure.

## Commands

`make setup`, `make check`, `make dev-api`, `make dev-web`.
Offline commands: `uv run --locked netatlas config-check`, `example`, `schema`.
README contains configuration, URLs, and individual check commands.

## Validation and publication

- `make setup`: locked Python/npm installation succeeds without a database or Docker.
- `make check`: passed; 12 Python tests and 3 web tests, Ruff lint/format, strict mypy,
  Biome recommended checks, TypeScript, Python wheel/source build, Vite production
  build, and offline CLI smoke checks. Python tests produce no warnings.
- Live local smoke: API health and synthetic observation through the Vite proxy
  return valid responses. Browser inspection confirms the rendered shell and local
  API connectivity. No real service was measured.
- npm installation audit reported zero vulnerabilities at validation time; this is
  not a comprehensive security audit. npm may mention an unapproved optional macOS
  `fsevents` install script; it is not needed for the validated setup/build.
- Private repository: https://github.com/sebastienlato/NetAtlas; delivery branch `main`.
  The Quality workflow runs `make setup` and `make check` on GitHub. Git history and
  Actions are authoritative for the delivery commit and its remote CI status.
- Verify publication with `git rev-parse HEAD`, `git ls-remote origin refs/heads/main`,
  and `git status --porcelain`. The first two hashes must match; the last output must
  be empty. Generated artifacts and local dependencies are intentionally ignored.

## Limitations and blockers

The UI is a foundation preview with a decorative globe, not working geographic
search. API health checks only process liveness; data is synthetic. No public service
security posture is claimed. Docker is not installed and is unnecessary in this phase;
Phase 4 will need an available local PostgreSQL/PostGIS runtime. No blocker to Phase 1.
Public licensing and a public operator contact remain release/real-campaign decisions.

## Next

**Phase 1 — Bounded Discovery Engine**, acceptance criteria in ROADMAP. The exact
self-contained kickoff is saved in `docs/NEXT_PHASE.md`. Begin it in a new Work chat;
do not implement it in the Phase 0 chat. All needed project state is in this repository.
