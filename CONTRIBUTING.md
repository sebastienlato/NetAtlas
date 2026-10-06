# Development and phase handoff

## Working agreement

Read the state, roadmap, architecture, decisions, and security policy first. Finish
one phase per Work chat; keep routine technical decisions autonomous. Ask only for
actual blockers requiring credentials, permission, or a manual action. Do not use
conversation history as a substitute for repository documentation.

Run commands in the repository root. `make setup` installs locked dependencies;
`make check` runs the complete proportional validation through Phase 14.
Use `make check-db` for the complete database acceptance suite; plain `make check`
reports those tests skipped without `NETATLAS_TEST_DB=1`. See `docs/STORAGE.md` for
Compose setup, standalone Compose override and isolated database/restore testing. Individual commands
are in README. Avoid repeated broad checks without a code change or new concern.
Use synthetic documentation addresses for committed fixtures and explicitly scoped
loopback integration servers. No tests should connect to arbitrary public services.
Offline rules and derived contracts are documented in `docs/FINGERPRINTS.md`.
Enrichment datasets/results are independent; use explicit clocks and checksum-pinned
local files, retain attribution, and see `docs/ENRICHMENT.md` for bounds and stale
semantics. Downloads/generated subsets remain ignored. Real IP datasets are not
measurement authorization.
Search contracts, count/clock semantics and workload reproduction are in
`docs/SEARCH.md` and `docs/SEARCH_BENCHMARK.md`. Keep queries out of collection; the Phase 7 HTTP adapter reuses search semantics
through separate allowlisted models and a generated client contract; do not test search with Internet measurements.
Read `docs/OPERATIONS.md` for the local deployment, service-role recovery, telemetry,
retention and stopped-restore runbook, and `docs/DEPENDENCIES.md` for the audit record.
Do not test resource failure by disrupting the owner DB or filling its disk.
See `docs/DISTRIBUTED.md` for authenticated workers, one-use permits, failure drills,
spool/credential recovery and restore quarantine. Never treat delivery retries as new
measurements, or reset boot generations/owner volumes to restart.
See `docs/SCHEDULING.md` for authored universes, exact coverage denominators,
seed-only IPv6, explicit snapshots/refreshes, bounded queue fairness and durable stop.
No fixture plan authorizes documentation-address execution or live routing acquisition.
See `docs/INSPECTION.md` for preview/trace limits and retention checks.
See `docs/GEOGRAPHIC_UI.md` for the explicit offline seed and browser acceptance.
Install Chromium once with `npm --prefix web exec -- playwright install chromium`;
full check-db also runs production-build browser tests on isolated synthetic storage.
See `docs/API.md` for local access, cursor and error policy. Run
`uv run --locked python -m netatlas.read_api.contract` after HTTP contract changes;
make check verifies generated TypeScript drift. Do not expose private dictionaries.
Update rule/pack versions when semantics change, retain provenance, and extend the
labeled synthetic corpus. Do not treat fixture-only signatures as real coverage.
Changes to shared syntax/matching semantics require an engine-version review;
replay uses the archived source/pack and the identified engine version.

Use Python type hints and explicit schemas at I/O boundaries. Keep domain types
free from I/O and side effects at import. React renders captured content as text,
never injected HTML. Keep implementation and tests small and focused on observable
behavior, limits, failure handling, and meaningful contracts.

Phase 13 evaluation is a separate operator command: read `docs/EVALUATION.md`, then
run the fixed bounded experiment with an explicit recent UTC clock, `--synthetic`,
optional `--measure` for four authored loopback services, and a new ignored output.
Commit authored aggregate analysis, never measured sources, JSON reports or temporary
datasets. Do not change production rules to improve this purposive corpus's scores.
Keep zero-denominator precision/recall undefined and unsupported classes visible.

## Dependency changes

Use `uv add` / `uv add --dev` and `npm --prefix web install` when changing dependencies.
Commit `uv.lock` and `web/package-lock.json`. Setup/CI use `uv sync --locked` and
`npm ci`, not unconstrained upgrades. Upgrade runtime pins and locks together when
needed, record why in DECISIONS, and rerun the relevant checks. Do not add secrets
to manifests, registries, command arguments, or lockfiles.

## Config and data

Built-in defaults are mirrored by `config/default.toml`, checked by tests. Local
overrides belong in ignored `config/local.toml`; configuration errors fail closed.
Use ignored `data/` for spool/observation files. Storage accepts authored synthetic inputs only; real ingestion is not enabled.
Never edit a shipped migration; add a new revision and test upgrade/restore. Keep
file publication/cleanup under the storage transaction lock, and never acknowledge
a row before commit. Follow retention/suppression and backup handling in STORAGE.
Do not put measured evidence,
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

## After the final roadmap phase

Phase 14 hands off a candidate with public source, not a new implementation phase. Follow
`docs/NEXT_PHASE.md`, `docs/PUBLICATION.md` and `docs/RELEASE_CANDIDATE.md`. Source-only
publication was authorized October 6, 2026. Licensing, public hosting and explicit
tag/release authorization remain separate owner/university decisions. Commit authored
demo/presentation sources, not generated decks, screenshots, measured JSON or local
identity ledgers. `docs/INSTALLATION.md` qualifies fresh-checkout rehearsal and first
downloads versus offline reuse. Keep the original evaluation report historical.
