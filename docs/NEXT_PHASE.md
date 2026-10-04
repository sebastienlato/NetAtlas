# PHASE 3 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
The opened NetAtlas folder is the repository root. Complete exactly Phase 3 in this
fresh Astra High Work chat; do not begin Phase 4.

First read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md,
DECISIONS.md, CONTRIBUTING.md, SECURITY.md, docs/DATA_MODEL.md, docs/DISCOVERY.md and
docs/PROTOCOL_EVIDENCE.md. Inspect Git status/remotes, toolchains, code and tests.
Repository files are authoritative; no earlier chat history is required. Respect
existing user changes and make routine engineering decisions autonomously.

Phase 2 delivered package 0.3.0 on Python 3.14/uv with FastAPI/Pydantic and a
React/TypeScript/Vite shell. Configuration is version 3, observations/manifests are
version 2, with an explicit legacy observation-v1 reader. The bounded asyncio worker
retains strict literal IPv4/IPv6 scope, small CIDRs, conservative pinned policy,
exclusions/opt-outs, shared global/per-prefix pacing, queue/concurrency limits,
deadlines, cancellation and private ignored JSONL/manifest output under data/.
CLI defaults dry-run; dialing requires enabled operator identity plus --measure.
Protocol collection separately requires measurement.protocol_evidence = true.
Lab mode accepts only literal 127.0.0.1 and ::1. API/UI cannot start measurements.

Collectors identify HTTP, TLS, SSH and SMTP from bounded handshake syntax, never
from conventional ports. Strategy greeting-http-tls-v1 permits at most two admitted
connections, two GET / requests and one TLS handshake per endpoint, with cumulative
receive/send/retention budgets including TLS records. SSH/SMTP are greeting-only;
bare 220 remains ambiguous. TLS preserves unverified DER/negotiation evidence,
including self-signed/expired certificates when the handshake succeeds. There is
no DNS, SNI, named Host, redirects, cookies, authentication, mail or STARTTLS.
Raw evidence is bounded base64; metadata remains hostile peer assertion. TCP
reachability is separate from protocol outcome. Review documented coverage gaps.

Phase 2 validation passed make check with 67 Python and 3 web tests plus lint,
strict types, builds and offline CLI smoke; the 39 protocol tests also passed with
warnings treated as errors. Verify results yourself. TLS fixtures require the
OpenSSL CLI and generate ephemeral keys/certificates in temporary directories.
No new package dependency, real Internet dataset/campaign, rule pack, category
engine, database, search, geography, distributed worker, release or tag exists.

Implement Phase 3 — Fingerprints and Categories: versioned deterministic rule packs,
evidence/confidence and a documented device-category taxonomy. Keep derivations
separate from collectors, immutable observations, storage and API. Define stable
rule identifiers/versions and pack provenance; produce reproducible derived records
linked to source observation IDs and precise bounded evidence selectors. Reprocessing
with the same pack must be deterministic; a changed pack must be distinguishable and
must not rewrite raw observations. Explicitly handle v1/v2 input compatibility,
missing/truncated/malformed evidence and unknown protocols.

Use a small labeled synthetic corpus to exercise positive, negative, ambiguous and
conflicting cases, false positives, confidence semantics and reprocessing. Cover the
planned taxonomy without claiming every device class is detectable: web services,
cameras/NVRs, routers, NAS, printers, SSH, VPN appliances, mail, databases, IoT and
industrial systems may remain unknown when evidence is insufficient. A protocol
alone does not establish a device category or product. Preserve multiple candidates
where justified and explain uncertainty. No vulnerability or exploitation claims.

Provide a bounded offline path to apply/inspect the rules and validate its output.
Treat rules and inputs as untrusted data: no executable rule code, arbitrary imports,
unsafe deserialization, active HTML/URL handling or unbounded regex/input processing.
Document evidence minimization and avoid logging raw content. Do not expand network
probes or bypass existing traffic/policy limits to fill fingerprint gaps. Use only
synthetic/documentation-address corpus records and explicit loopback fixtures;
never public targets, commercial device-search databases or mandatory paid APIs.

Do not add credential guessing, authentication bypass, exploitation, persistence,
remote modification or destructive actions. Stay within Phase 3: no durable database,
ingestion pipeline, geolocation, search infrastructure, distributed workers, releases
or tags. Ask only for genuine blockers, credentials, permissions or unavoidable
manual actions after completing independent authorized work. Keep tests meaningful
and proportionate; do not introduce routine approval gates.

At completion run relevant checks and make check; update authoritative docs with
actual results, limitations and state; replace docs/NEXT_PHASE.md with a self-contained
Phase 4 kickoff; review tracked files/diff for secrets, captures and generated data;
commit with a Phase 3 message; push; verify local HEAD equals the remote delivery
branch and the working tree is clean. Report delivery, checks/results, commit hash,
push/CI status, blockers and exact current state. Include the complete Phase 4 kickoff,
then stop.
