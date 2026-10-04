# Project state

Updated: 2026-10-04. **Phase 3 — Fingerprints and Categories is complete.**
Phase 4 has not started. Package **0.4.0**; config **3**; observation/manifest **2**;
rule-pack/derivation schemas **1**; engine **fingerprints-1**;
taxonomy **netatlas-categories-1**.

## Delivered

- Phase 1 bounded literal IPv4/IPv6 discovery, pinned conservative policy,
  exclusions/opt-outs, small CIDRs, narrow loopback lab mode, shared global/per-prefix
  pacing, bounded queue/concurrency/deadlines/cancellation and private spool retained.
- Phase 2 opt-in HTTP/TLS/SSH/SMTP protocol evidence retained. Port-independent
  greeting/GET/TLS strategy admits at most two connections, two GETs and one TLS
  handshake per endpoint through shared policy/rate gates. Cumulative payload
  send/receive/retention caps include TLS records. No DNS/SNI, redirects, cookies,
  authentication, mail, STARTTLS, crawling or state-changing interactions.
- Phase 3 bounded declarative JSON packs, pure offline derivation engine, source and
  pack content hashes, stable rule IDs/versions, taxonomy and precise bounded byte
  references. Original observations are immutable; v1/v2 reads remain explicit.
- Core pack 1.0.0 contains four rules for nginx, OpenSSH and Postfix assertions.
  Separate product/category outputs, asserted/corroborated confidence semantics,
  unknowns and retained multiple/conflicting candidates. No product-version or
  vulnerability inference. All 11 planned positive category IDs are documented;
  fictional test signatures exercise them without claiming real device coverage.
- `netatlas fingerprint --inspect`, `--input ... --output ...`, and
  `--input ... --validate ...`: bounded regular-file offline application and full
  deterministic replay validation. Private no-clobber output under ignored data/,
  atomic publication, stable generic diagnostics, no raw-content duplication.
- Raw syntax is reparsed instead of trusting metadata/ports or old embedded
  fingerprints. Shared I/O-free parsers moved byte-for-byte to `protocol_syntax.py`;
  collectors retain compatibility exports and unchanged traffic behavior.
- API health/web shell describe Phase 3. They still cannot start measurements,
  classify uploaded data, query stored observations or display captured evidence.

## Architecture now

Python 3.14/asyncio/FastAPI/Pydantic; React/TypeScript/Vite shell. `collectors/`
handles bounded evidence acquisition; `discovery/` owns policy/admission/campaigns;
`domain.py`, `evidence.py`, `observation.py` are I/O-free contracts.
`derivations/models.py` and `engine.py` implement separate rules/results and pure
matching; `offline.py` owns bounded file I/O. Both collectors and derivations use
shared syntax parsing without depending on each other's execution layer.

No durable database, ingestion/outbox pipeline, blob store, search, geography,
distributed workers or Internet dataset. PostgreSQL/PostGIS, optional OpenSearch
and MapLibre remain planned. No Internet campaign, release or tag was created.

## Commands and validation

`make setup`, `make check`, `make dev-api`, `make dev-web`; see README and
`docs/DISCOVERY.md`, `docs/PROTOCOL_EVIDENCE.md`, `docs/FINGERPRINTS.md`,
`docs/DATA_MODEL.md`. Fingerprinting does not require measurement settings.

- Phase 2 baseline reverified: **67 Python and 3 web tests**, full `make check` passed.
- Phase 3 final: **130 Python and 3 web tests**; `make check` passed Ruff/format,
  strict mypy, Biome/TypeScript, Python wheel/source and Vite builds, offline smoke.
- Entire Python suite also passed **130 tests with warnings treated as errors**.
  The fingerprint suite contributes **63 tests**, including **47 labeled corpus
  cases** (22 core, 25 fictional taxonomy/ambiguity/encoding cases).
- Corpus positives/negatives, deliberately spoofed product assertion, insufficient
  category evidence, conflicting candidates, v1/v2 and legacy-shaped v2, malformed/
  missing/truncated/encoded content, forged metadata, body/record/pack bounds,
  hostile rules/JSON/file types, trace ranges/hashes, pack changes, deterministic
  replay, no networking, private no-clobber output and redacted failures tested.
- Initial full validation exposed an intermittent existing loopback TLS fixture
  cleanup race. Fixture shutdown now drains ready accept callbacks and transport
  creation before closing the listener, avoiding Python 3.14 late-attach failures.
  No warning suppression or production collector change; the 39 protocol tests
  and entire suite pass with warnings as errors after the fix.
- Verified shared parser move is byte-identical and built wheel includes core.json.
  Only synthetic/documentation-address records and explicit loopback tests. TLS keys
  and certificates are generated temporarily with OpenSSL, never committed.
- Runtime pins unchanged: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0.
  No new package/service dependency; uv.lock changes only NetAtlas's version.

Private repository: https://github.com/sebastienlato/NetAtlas; delivery branch `main`.
Quality CI runs `make setup` and `make check` on Linux. Git history and Actions are
final commit/CI authority. Verify `git rev-parse HEAD` equals
`git ls-remote origin refs/heads/main` and `git status --porcelain` is empty.

## Limitations and blockers

No Phase 3 implementation blocker. Real campaign operator authority/contact and
network/institutional permission remain separate prerequisites. No real target was
measured. Rules observe peer assertions; even corroborating fields can be spoofed.
Confidence is ordinal, not a probability or authenticated identity. Core device
classes beyond three service roles remain unknown. No real-world precision/recall,
physical-device identity, operating-system, firmware or vulnerability claim.

Matching covers literal HTTP Server/body-window, SSH software and explicit SMTP
text only. No TLS certificate identity parsing, body decompression/chunk decoding,
HTML/URL handling or added probes. Malformed HTTP headers supply no fields; complete
headers may survive body truncation. Absent evidence is not a negative finding.
Derivation records carry no processing clock; later operational runs may separately
record it. Preserve source and pack snapshots plus engine version for replay.

Offline file limits: 128 KiB packs, 64 rules × 4 conditions, 16 MiB input/1024 rows,
1 MiB per row, 32-level JSON nesting, 8192-byte body windows, 128 candidates per
record, 32 MiB output. No ingestion batching, deduplication, crash recovery,
authenticated pack distribution, real-data access/redaction/retention policy or
adversarial-local-user filesystem protection. Private evidence selectors/digests
still require careful handling. Output atomicity is not power-loss durability.

Protocol coverage gaps persist: default IP virtual host only, no named Host/SNI,
STARTTLS, HTTP/2–3, full SSH exchange, retries or legacy TLS downgrade. Unverified TLS
certificates are retained only after successful OpenSSL handshakes. TCP-open and
protocol outcome remain distinct. Payload budgets exclude TCP/IP overhead, kernel
buffers/retransmits and bytes sent by a peer after closure.

Budgets cover one campaign; spool lock is not host-wide/distributed coordination.
No resume/crash recovery/routing assurance/hot opt-out reload/fairness guarantee.
API/UI remain unauthenticated loopback development components. Public licensing
and deployment remain owner decisions, not blockers to this completed phase.

## Next

**Phase 4 — Durable Observation Pipeline**, in a fresh chat using `docs/NEXT_PHASE.md`.
Do not start it in this Phase 3 chat. Repository files hold the complete handoff.
