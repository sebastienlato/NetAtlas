# Development and phase handoff

## Working agreement

Read the state, roadmap, architecture, decisions, and security policy first. Finish
one phase per Work chat; keep routine technical decisions autonomous. Ask only for
actual blockers requiring credentials, permission, or a manual action. Do not use
conversation history as a substitute for repository documentation.

Run commands in the repository root. `make setup` installs locked dependencies;
`make check` runs the complete proportional Phase 0 validation. Individual commands
are in README. Avoid repeated broad checks without a code change or new concern.
Use synthetic documentation addresses for committed fixtures and explicitly scoped
loopback integration servers. No tests should connect to arbitrary public services.

Use Python type hints and explicit schemas at I/O boundaries. Keep domain types
free from I/O and side effects at import. React renders captured content as text,
never injected HTML. Keep implementation and tests small and focused on observable
behavior, limits, failure handling, and meaningful contracts.

## Dependency changes

Use `uv add` / `uv add --dev` and `npm --prefix web install` when changing dependencies.
Commit `uv.lock` and `web/package-lock.json`. Setup/CI use `uv sync --locked` and
`npm ci`, not unconstrained upgrades. Upgrade runtime pins and locks together when
needed, record why in DECISIONS, and rerun the relevant checks. Do not add secrets
to manifests, registries, command arguments, or lockfiles.

## Config and data

Built-in defaults are mirrored by `config/default.toml`, checked by tests. Local
overrides belong in ignored `config/local.toml`; configuration errors fail closed.
Use ignored `data/` for future spool/observation files. Do not put measured evidence,
captured sensitive content, geolocation databases, caches, generated artifacts, or
operator credentials into fixtures or Git. Commit small synthetic test data only.

## Phase completion checklist

1. Check the phase's acceptance criteria and its limits in ROADMAP.
2. Run `make check` and any genuinely phase-specific integration/behavior checks.
3. Review the diff and tracked file list for accidental data/secrets/build outputs.
4. Update PROJECT_STATE (what actually works, validation, limitations, blockers),
   architecture/decisions/roadmap as appropriate, and `docs/NEXT_PHASE.md`.
5. Commit with a clear phase-specific message. Push when a remote exists.
6. Compare `git rev-parse HEAD` with `git ls-remote origin refs/heads/main` (or the
   actual delivery branch), and verify `git status --porcelain` is empty. Use the
   actual committed status, not an anticipated result. Inspect GitHub CI if available.
7. Report delivery, checks, commit, push status, blockers, and exact current state;
   include the full next-phase kickoff and stop. Do not begin the next phase.

PROJECT_STATE cannot contain its own final commit hash without a circular update.
Record phase identity and reproducible verification commands there; Git history and
the completion report identify the exact commit. If publication is blocked, preserve
the completed local commit and ask only for the minimum missing owner action.
