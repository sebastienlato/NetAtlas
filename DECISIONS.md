# Architecture decision record

Accepted 2026-10-04. Revisit with evidence; record consequences rather than silently
changing the design. Phase 4 adds the local durable pipeline; geography/search and distributed infrastructure
remain planned.

| ID | Choice and reason | Consequences / reconsider when |
| --- | --- | --- |
| ADR-001 | Modular monorepo; Python domain/config/worker/API package and separate web directory. Easy local use and independent module testing. | Split deployments, not repositories, when worker isolation is needed. |
| ADR-002 | Python 3.14, asyncio, FastAPI, Pydantic v2; available local runtime, structured asynchronous I/O, typed contracts and schema generation. | Python TCP connect discovery is the initial correctness baseline. Benchmark before considering native/ZMap adapters; no global-scale throughput claim. |
| ADR-003 | uv and `uv.lock`; npm and `package-lock.json`; exact local runtime pins. | Setup uses locked installs. Node 26.8.1 is the verified local version, not an assertion of LTS status. Refresh pins deliberately; CI uses the same versions. |
| ADR-004 | React + TypeScript + Vite; Biome, Vitest, Testing Library. | Small typed shell now; MapLibre, map assets and generated API client arrive with the real UI. No mandatory commercial map SDK. |
| ADR-005 | PostgreSQL/PostGIS authoritative storage; JSONL before persistence phase. | Phase 4 uses SQLAlchemy/Alembic, psycopg and pinned PostgreSQL Compose. PostGIS arrives in Phase 5; no SQLite substitute. |
| ADR-006 | PostgreSQL search first; optional OpenSearch projection after benchmarks. | One data service for a small demonstration; durable history/outbox permits later index replacement. |
| ADR-007 | Versioned observation envelope, immutable evidence and separate versioned derivations. | More provenance than a mutable host row, but supports historical search and reproducible classification. No unsupported inference that an IP equals one physical device. |
| ADR-008 | Literal targets, disabled measurement defaults, constrained configuration, loopback fixture tests. | Phase 1 implements traffic policy before dialing. No browser-triggered network probing. |
| ADR-009 | Free downloadable data and offline/self-hosted maps. | License/provenance/refresh tracking required. No mandatory geolocation API, tile account, paid cloud, or commercial discovery source. |
| ADR-010 | Start as local processes, later Compose/worker containers; database leases before a broker. | Defer orchestration complexity until throughput/failure measurements justify it. |
| ADR-011 | Private GitHub repository named NetAtlas; no release/tag/license grant yet. | Protect unpublished thesis work and defer public licensing to a genuine publication decision. |
| ADR-012 | One meaningful phase per chat, with docs, validation, commit, remote verification, and repository-held handoff. | New conversations never depend on inaccessible previous chat context. |
| ADR-013 | Configuration v2 enables explicit opt-in discovery; software v0.2.0. CLI additionally requires `--measure`; API has no scan controls. | Operator syntax validation is not verification of authority; contact and research user-agent are metadata until protocol collectors exist. |
| ADR-014 | Conservative pinned IANA deny prefixes, runtime non-global/multicast checks, IPv6 2000::/3 restriction; allowlists only narrow; lab accepts two literal loopback addresses. | Some globally reachable special-purpose services are deliberately omitted. No live routing or hot opt-out reload; stop, update, preview and restart. |
| ADR-015 | Hard scope caps, streaming seeded network/port ordering with address rotation, shared no-burst pacing and bounded asyncio queue/workers. | Reproducible admission order without a full target list; conservative head-of-line blocking accepted. No global-scale, fairness, packet-rate or distributed-budget claim. |
| ADR-016 | Raw socket ownership for connect-only work, immutable observation v1 (`closed` plus `connection_refused`), private JSONL and manifest v1. | No application bytes or protocol inference; no unnecessary observation schema break. Cancellation records incomplete attempts in manifest, flushes completed rows and closes sockets. |
| ADR-017 | Atomic manifest replacement, graceful final fsync/checksum, advisory per-spool campaign lock. | Small synchronous local file writes are sufficient for Phase 1; no crash recovery, host-wide lock or durable ingestion claim. macOS/Linux supported; Windows port is deferred. |

| ADR-018 | Package 0.3.0, config v3, observation/manifest v2; explicit legacy v1 reader, no silent rewrite. Protocol mode defaults false. | Existing connect-only invocation behavior is retained; explicit config-v2 files require reviewed migration. |
| ADR-019 | Port-independent greeting → one GET if silent → at most one fresh TLS attempt for unidentified HTTP/EOF. Every connection shares admission. | At most two connections, two GETs and one TLS handshake per endpoint. Unknown unsolicited greetings receive no commands. SSH/SMTP are greeting-only, bare 220 ambiguous. |
| ADR-020 | Raw socket payload I/O and SSLObject/MemoryBIO, cumulative receive/send/retention caps; separate connect/interaction/endpoint/campaign deadlines. | TLS record traffic cannot bypass accounting. No hidden stream prefetch, retry, DNS, SNI or downgrade; kernel traffic/overhead is outside payload counters. Endpoint timer starts after first admission and includes later admission waits. |
| ADR-021 | Preserve bounded peer DER chain with negotiated TLS metadata, verification explicitly not performed; no parsed identity trust claim. | Expired/self-signed captures work when OpenSSL completes the handshake; obsolete or structurally invalid handshakes may expose no certificate. No trust/OCSP/AIA request or client certificate. |
| ADR-022 | Strict bounded syntax recognition, opaque base64 captures and typed metadata, independent TCP/interaction outcomes. | No product/device inference. Header values and greetings remain untrusted; no decoding active content. Connect-open persists through application errors. No durable ingestion or public evidence view. |

| ADR-023 | Package 0.4.0; unchanged config v3 and observation/manifest v2; separate rule-pack/derivation schema 1. | Legacy foundation fingerprints are not detection inputs or mutated outputs. Explicit v1/v2 offline reads preserve source identity and content. |
| ADR-024 | Bounded declarative literal rules, no dynamic regex/code; I/O-free syntax parsers shared by collectors and derivations. | Reparse raw syntax rather than trusting metadata. No traffic changes, network lookups, body decoding or new dependencies. |
| ADR-025 | Source/pack canonical hashes, engine/taxonomy versions and precise raw-byte references; deterministic output omits processing clock. | Store operational processing times separately later. Same-version pack edits remain distinguishable; digests do not authenticate authorship. |
| ADR-026 | Independent product/category candidates with asserted/corroborated ordinal confidence, unknowns and retained multiple candidates. | Confidence is not calibrated probability or identity proof. Core supports nginx/OpenSSH/Postfix assertions only; fictional taxonomy pack is explicitly synthetic. |
| ADR-027 | Bounded streaming offline apply/inspect/replay CLI, private staged no-clobber output under ignored data/. | Stable generic errors and no raw-content duplication. No ingestion, deduplication, crash recovery, durable storage or public evidence interface. |

| ADR-028 | Package 0.5.0; storage migration head 0002; unchanged config/observation/derivation wire schemas. | Storage is an independent local CLI/library; collectors, API and UI do not gain ingestion or querying. |
| ADR-029 | UUID plus canonical source hash, extracted SHA-256 raw blobs, private JSONB envelopes and immutable history triggers. | Equal content shares files, never measurement history; reconstruct/hash original v1/v2 evidence and retain independent packs/results. |
| ADR-030 | Single PostgreSQL advisory transaction lock, fsynced files before synchronous commit, acknowledgements after commit. | Correctness baseline for local use; orphan GC and retention use the same lock. Distributed throughput requires a later design. |
| ADR-031 | Separate latest attempt/open/evidence pointers ordered by finish/start/UUID. | Negative, stale and empty attempts preserve previous evidence; UUID tiebreak is deterministic, not physical chronology. |
| ADR-032 | Transactional outbox with per-consumer receipts and an idempotent same-DB mirror. | Atomic DB effects only; replay reads live source truth. External consumers need deletion/idempotency contracts before adoption. |
| ADR-033 | Synthetic-only ingestion; private local owner access; 30-day source expiry; whole-record redaction/removal and persistent CIDR suppression. | No public raw view or silent evidence edits. Explicit maintenance, 90-day replay tombstones, separately managed spools and 7-day backup policy; production roles/encryption remain deferred. |
| ADR-034 | Pinned PostgreSQL 18.3 image/digest, two Alembic migrations, coordinated DB/blob backup and empty-database restore. | Real PostgreSQL integration required in CI. Local tests use generated credentials and isolated disposable databases; no real data or Internet probes. |

## Primary references consulted

- [Python task groups/timeouts](https://docs.python.org/3/library/asyncio-task.html)
- [FastAPI asynchronous execution](https://fastapi.tiangolo.com/async/)
- [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/)
- [uv locking and synchronization](https://docs.astral.sh/uv/concepts/projects/sync/)
- [Vite setup and runtime requirements](https://vite.dev/guide/)
- [PostGIS spatial indexes](https://postgis.net/documentation/faq/spatial-indexes/)
- [IANA IPv4 special-purpose registry](https://www.iana.org/assignments/iana-ipv4-special-registry/)
- [IANA IPv6 special-purpose registry](https://www.iana.org/assignments/iana-ipv6-special-registry/)
- [OpenStreetMap data licensing](https://www.openstreetmap.org/copyright)

These references support the component choices; they are not claims that the
future system has already implemented or validated those capabilities.
