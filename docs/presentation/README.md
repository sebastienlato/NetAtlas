# Thesis presentation source

The authored `build.mjs` creates an editable 12-slide candidate deck with speaker
notes and local repository citations. Run it using the Codex bundled Node runtime
and `@oai/artifact-tool` from the Presentations skill. That optional authoring library
is **not a NetAtlas runtime dependency**. Set `SKILL_DIR` to the installed Presentations
skill, `NETATLAS_DECK_BUILD` and `NETATLAS_DECK_OUTPUT` to new absolute directories under
ignored artifacts/, `RUNTIME_PYTHON` to the bundled Python and `RUNTIME_NODE_MODULES` to the bundled
package directory. Link docs/presentation/node_modules to that package directory
for ES-module resolution (the link is ignored by Git).
The exported candidate, final deck and all renders stay private. The script refuses an
existing final filename. DEMONSTRATION is the portable source for the live speaking
sequence and exact commands, independent of any presentation tool.

The slides cite Phase 13 measurements as historical findings. Phase 14 rehearsal
and check evidence lives in RELEASE_CANDIDATE. No slide grants publication rights.
Generated screenshots are local rehearsal records, never measured production data.

With the freshly seeded thesis profile served on port 8000 and project web dependencies
installed, run `node docs/presentation/rehearse.mjs DATASET_SHA256` from repository root.
This performs only read interactions and saves screenshots plus a private exact-source
identity ledger under artifacts/phase14/rehearsal. The browser refuses external requests.
It requires the installed Playwright Chromium cache and does not download anything.
