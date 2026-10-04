# PHASE 2 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
The opened NetAtlas folder is the repository root. Complete exactly Phase 2 in this
fresh Astra High Work chat; do not begin Phase 3.

First read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md,
DECISIONS.md, CONTRIBUTING.md, SECURITY.md, docs/DATA_MODEL.md and docs/DISCOVERY.md.
Inspect Git status/remotes, toolchains, existing code and tests. Repository files
are authoritative; no earlier chat history is required. Respect existing user changes.

Phase 1 delivered package 0.2.0 on Python 3.14/uv with FastAPI/Pydantic and a
React/TypeScript/Vite shell. The modular asyncio connect-only worker supports
bounded literal IPv4/IPv6 scope, strict small CIDRs, streaming seeded ordering,
conservative pinned IANA-derived policy, exclusions/opt-outs, shared global/per-prefix
pacing, bounded queue/concurrency, deadlines, graceful cancellation and socket cleanup.
CLI defaults dry-run; measurement requires enabled operator configuration plus
`--measure`. Lab mode accepts only literal 127.0.0.1 and ::1. Version-1 observations
and manifests are private ignored JSONL/local files under data/. Config version is 2.
There is no protocol collector, real Internet dataset, database, search or geographic
implementation. API/UI cannot initiate scans. Phase 1 validation comprises 28 Python
and 3 web tests plus lint/types/build/offline smoke; verify current results yourself.

Implement Phase 2 — Protocol Evidence: a modular collector interface and HTTP, TLS,
SSH and SMTP collectors using bounded ordinary unauthenticated handshakes. Preserve
separation among discovery, collectors, domain, storage and API. Identify protocols
from handshake evidence independently of conventional port numbers; retain honest
unknown/ambiguous results. Plan and document a small, bounded probe-selection strategy
and its traffic cost. Apply the same eligibility and global/per-prefix budgets to
**every new connection**, including additional collector connections; do not silently
multiply traffic. Keep dry-run previews accurate about planned interactions and caps.

Capture only bounded necessary raw evidence and typed protocol metadata. Evolve the
observation schema explicitly with schema version and compatibility tests where
needed; retain campaign/config/policy/scanner provenance and JSONL/manifest integrity.
Implement HTTP without redirects, cookies, credentials, crawling or state-changing
requests; retain bounded headers/status/body evidence. Preserve TLS certificate and
negotiation evidence, including invalid/self-signed cases, without treating identity
assertions as trusted. SNI/Host names, if supported, require explicit provenance and
must not add unbounded DNS. SSH/SMTP greeting/handshake collection must never attempt
authentication or send mail. No protocol inferred solely from its port. No fingerprint
rule packs, device categories, vulnerability claims or Phase 3 work.

Use only synthetic and explicit loopback fixture services, including services on
unconventional ports and malformed, binary, slow and oversized responses. Validate
connect/interaction/total deadlines, cumulative byte and connection caps, all outcome
semantics, cancellation/socket cleanup, hostile-content handling and evidence encoding.
Cancellation must stop new work, flush completed observations and close resources.
Preserve conservative production policy and narrow lab scope; an allowlist cannot
override special-use, multicast, non-global, excluded or opt-out denials. No Internet
services or sweeps as smoke tests. Never add credential guessing, authentication
bypass, exploitation, persistence, destructive actions or remote modification. Do not
depend on commercial device-search databases or mandatory paid APIs.

Make routine engineering decisions autonomously. Ask only for genuine blockers,
credentials, permissions or unavoidable manual actions after completing independent
work. Keep testing proportionate. Do not add durable persistence, distributed workers,
geolocation, search infrastructure, releases or tags in this phase.

At completion run relevant validation and make check; update authoritative docs with
actual results, limitations and state; replace docs/NEXT_PHASE.md with a self-contained
Phase 3 kickoff; review tracked files/diff for secrets, captured data and generated
artifacts; commit with a Phase 2 message; push; verify local HEAD matches the remote
delivery branch and the working tree is clean. Report delivery, checks/results, commit
hash, push/CI status, blockers and exact current state. Include the complete Phase 3
kickoff, then stop.
