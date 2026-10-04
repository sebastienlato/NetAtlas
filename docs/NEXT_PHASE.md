# PHASE 1 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
The opened NetAtlas folder is the repository root. Complete exactly Phase 1 in this
fresh Astra High Work chat; do not begin Phase 2.

First read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md,
DECISIONS.md, CONTRIBUTING.md, SECURITY.md, and docs/DATA_MODEL.md. Inspect Git
status/remotes, the installed toolchains, and existing code/tests. These files are
authoritative; no earlier chat history is required. Phase 0 established a Python
3.14/uv/FastAPI/Pydantic package, validated TOML settings and observation contracts,
a local API and React/TypeScript/Vite web shell, locked dependencies, and CI. It has
no measurement engine or real data. Respect existing user changes.

Implement Phase 1 — Bounded Discovery Engine: a modular asyncio TCP connect worker
for explicit literal IPv4/IPv6 addresses and bounded small CIDRs/port sets; streaming
target generation; target eligibility and exclusions; global and per-prefix rate
budgets; bounded concurrency/queues; timeouts; cancellation/socket cleanup; honest
open/refused/timeout/error outcomes; structured redacted logging; and versioned JSONL
observations with a reproducible campaign manifest in ignored data/. Preserve domain
and API separation. No protocol collectors, fingerprints, database, or global sweep.

Add a CLI dry-run default that previews scope/policy without connections. Measurement
must require explicit enablement and validated operator identity. Evolve Phase 0's
disabled-only config deliberately. Production policy must deny non-global/special-use,
multicast and excluded/opt-out ranges; an allowlist cannot override those denials.
Provide only a narrowly scoped explicit loopback lab mode for fixture tests. Bound
target expansion before huge CIDRs can allocate memory or accidentally schedule vast
runs. Record configuration/policy versions, seed, campaign and scanner identities.
Enforce both global and per-prefix rates across concurrent tasks; ensure cancellation
flushes completed results and closes resources without scheduling additional work.

Use synthetic and loopback fixtures for meaningful tests, including eligibility,
address boundaries, open/refused outcomes, deterministic timeout/error handling,
rate/concurrency bounds, cancellation and JSONL/manifest integrity. Do not scan real
Internet services as a smoke test. Do not implement credential guessing,
authentication bypass, exploits, persistence, destructive operations, or changes to
remote devices. NetAtlas collects ordinary unauthenticated exposure and does not use
Shodan/Censys/commercial search data or mandatory paid APIs.

Make routine architecture/dependency/implementation choices autonomously. The owner
wants minimal friction and involvement. Ask only for a genuine blocker, credentials,
permission, or unavoidable manual action after completing independent work. Keep the
increment feasible within this single chat and avoid excessive microscopic tests.

When complete: run relevant validation and make check; update all authoritative docs
with actual results, limitations and state; replace docs/NEXT_PHASE.md with a fully
self-contained Phase 2 kickoff; review the diff/tracked files for secrets, captured
data and generated artifacts; commit with a Phase 1 message; push if a remote exists;
verify local HEAD equals the remote delivery branch and the working tree is clean.
Report what was built, checks/results, commit hash, push/CI status, genuine blockers,
and exact current state. Include the full Phase 2 kickoff in the response, then stop.
