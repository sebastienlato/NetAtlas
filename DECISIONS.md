# Architecture decision record

Accepted 2026-10-04. Revisit with evidence; record consequences rather than silently
changing the design. Phase 1 adds the bounded discovery modules; planned
infrastructure remains absent.

| ID | Choice and reason | Consequences / reconsider when |
| --- | --- | --- |
| ADR-001 | Modular monorepo; Python domain/config/worker/API package and separate web directory. Easy local use and independent module testing. | Split deployments, not repositories, when worker isolation is needed. |
| ADR-002 | Python 3.14, asyncio, FastAPI, Pydantic v2; available local runtime, structured asynchronous I/O, typed contracts and schema generation. | Python TCP connect discovery is the initial correctness baseline. Benchmark before considering native/ZMap adapters; no global-scale throughput claim. |
| ADR-003 | uv and `uv.lock`; npm and `package-lock.json`; exact local runtime pins. | Setup uses locked installs. Node 26.8.1 is the verified local version, not an assertion of LTS status. Refresh pins deliberately; CI uses the same versions. |
| ADR-004 | React + TypeScript + Vite; Biome, Vitest, Testing Library. | Small typed shell now; MapLibre, map assets and generated API client arrive with the real UI. No mandatory commercial map SDK. |
| ADR-005 | PostgreSQL/PostGIS authoritative storage; JSONL before persistence phase. | Avoid SQLite behavior differences and unnecessary database services now. SQLAlchemy/Alembic and container tooling deferred to Phase 4. |
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
