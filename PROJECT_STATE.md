# Project state

Updated: 2026-10-04. **Phase 2 — Protocol Evidence is complete.**
Phase 3 has not started. Package **0.3.0**; config **3**; observation/manifest **2**.

## Delivered

- Phase 1 bounded literal IPv4/IPv6 discovery, seeded streaming scope, pinned
  conservative policy, exclusions/opt-outs, small-CIDR and loopback restrictions,
  shared global/per-prefix pacing, bounded workers/queue and private spool retained.
- Modular HTTP/TLS/SSH/SMTP protocol evidence collection with explicit config opt-in.
  Port-independent greeting/one-GET plan, at most one additional TLS connection;
  every connection reuses the shared admission/policy gate. No hidden connect-only
  preflight, retries, DNS, SNI, redirects, cookies, credentials or state-changing work.
- Cumulative socket receive/send and raw-retention caps across both connections,
  including TLS records; connect, whole-interaction, endpoint and campaign deadlines.
  Raw sockets close on success, errors and cancellation. Initial pacing is outside
  the endpoint timer; subsequent admission waits are inside it.
- Typed status/headers/body-offset HTTP metadata, opaque bounded raw captures,
  unverified DER certificate chain and negotiation evidence, SSH identification,
  SMTP greetings and honest bare-220 SMTP/FTP ambiguity. No port-only inference.
- Observation v2, strict explicit v1/v2 compatibility reader, manifest v2 with actual
  connection counts and planned costs; config/policy/campaign/scanner provenance,
  JSONL checksum and cancellation integrity retained. Explicit old config-v2 files
  require reviewed migration; protocol mode defaults false.
- API health and web copy report Phase 2. The API/UI still cannot start measurements
  or expose captured evidence. The example remains explicitly synthetic.

## Architecture now

Python 3.14/asyncio/FastAPI/Pydantic; React/TypeScript/Vite shell. `collectors/` contains
passive protocol parsers, TLS handshake adapter, bounded I/O and probe selection.
Discovery supplies admission and campaign lifecycle; collectors do not depend on
storage/API. `domain.py`, `evidence.py`, `observation.py` are I/O-free contracts.

No fingerprint rule packs, device category engine, vulnerability claims, durable
pipeline/database, search, geolocation, distributed workers or Internet dataset.
No Internet campaign, release or tag has been created. PostgreSQL/PostGIS, optional
OpenSearch and MapLibre remain planned for their later roadmap phases.

## Commands and validation

`make setup`, `make check`, `make dev-api`, `make dev-web`; see README,
`docs/DISCOVERY.md`, `docs/PROTOCOL_EVIDENCE.md`, and `docs/DATA_MODEL.md`.

- Baseline verified: 28 Python and 3 web tests, lint/types/build/offline smoke passed.
- Phase 2: **67 Python and 3 web tests passed, without warnings**; full `make check`
  passed Ruff lint/format, strict mypy, Biome/TypeScript, wheel/source build, Vite build
  and offline CLI smoke.
- Protocol suite: **39 tests passed with warnings treated as errors**. Covers
  unconventional ports, fragmented/malformed/binary/slow/oversized responses,
  hostile content and base64, HTTP duplicate/framing bounds, no redirect/cookies,
  IPv6 Host/no DNS, TLS/HTTPS and wrapped greetings, self-signed/expired certificates,
  cumulative wire/retention/send caps, additional connection admission/pacing/denial,
  connect/interaction/endpoint/campaign deadlines, TCP/protocol outcome separation,
  cancellation during greeting/TLS/HTTP, socket cleanup and v1/v2 compatibility.
- Only synthetic/explicit loopback fixtures. TLS fixture keys/certificates are
  generated in temporary directories with OpenSSL, never committed. Test server
  ownership includes failed/cancelled TLS upgrades; no resource-warning suppression.
- Runtime pins verified unchanged: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0.
  No new package/service dependency; `uv.lock` changes only NetAtlas's version.

Private repository: https://github.com/sebastienlato/NetAtlas, delivery branch `main`.
Quality CI runs `make setup` and `make check` on Linux. Git history and Actions are
authoritative for final commit/CI status. Verify `git rev-parse HEAD` equals
`git ls-remote origin refs/heads/main` and `git status --porcelain` is empty.

## Limitations and blockers

No implementation blocker. Real campaign operator authority/contact and network or
institutional permission are separate prerequisites, not implied by development.
No real target was measured. Protocol identity is syntax-based peer evidence, not
proof of product/device identity or security. TLS certificates are explicitly
unverified; OpenSSL-rejected handshakes may expose no certificate. Only the default
IP virtual host is sampled. No STARTTLS, HTTP/2–3, decompression, crawling, named
hosts, legacy TLS downgrade, authentication, mail or full SSH key exchange.

A recognized protocol may have incomplete/malformed body evidence; TCP-open remains
open through interaction failures. Payload caps exclude TCP/IP overhead, kernel
buffers/retransmits and bytes sent by a peer after closure. Metadata remains hostile
and private. Real ingestion requires future access/redaction/retention controls.

Budgets cover one campaign; the advisory spool lock is not host-wide/distributed
coordination. No retries, resume, crash recovery, routing assurance, hot opt-out
reload or fairness guarantee. Stop, update config, preview and restart for an opt-out.
Graceful cancellation flushes completed endpoint observations; interrupted endpoints
are incomplete counts. Hard kill/power loss/disk failure can leave partial output.
API/UI remain unauthenticated loopback development components. Public licensing and
deployment remain owner decisions; no approval is needed to finish this phase.

## Next

**Phase 3 — Fingerprints and Categories**, in a fresh chat using `docs/NEXT_PHASE.md`.
Do not begin it in the Phase 2 chat. Repository files hold the complete handoff.
