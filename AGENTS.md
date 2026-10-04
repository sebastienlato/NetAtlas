# NetAtlas agent instructions

Read `PROJECT_STATE.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `DECISIONS.md`,
`CONTRIBUTING.md`, and `SECURITY.md` before changing the project. Repository files,
not chat history, are the authoritative project state.

- Complete exactly one roadmap phase per Work chat and stop after its handoff.
- Make routine engineering decisions autonomously; do not introduce approval gates.
- Stay within the requested phase. Do not represent planned modules as implemented.
- Never add credential guessing, authentication bypass, exploitation, persistence,
  or remote modification. Measurement is bounded normal unauthenticated interaction.
- Default development and tests to synthetic/loopback fixtures. Do not perform
  Internet sweeps as an implementation smoke test.
- Keep observations, credentials, local config, databases, datasets, and generated
  outputs out of Git. Use documentation addresses in committed fixtures.
- Keep scanner/collectors, domain, derivations, storage/search, API, and UI separable.
- Use `make check`; add meaningful tests for new behavior without microscopic gates.
- At phase completion: update authoritative docs and `docs/NEXT_PHASE.md`, review
  tracked files, commit, push if a remote exists, verify remote HEAD and a clean tree,
  report results and a self-contained kickoff, then stop.
- Do not create releases/tags before the roadmap's release phase.
- Ask the owner only for genuine blockers, credentials, permissions, or unavoidable
  manual actions after completing all independent authorized work.
