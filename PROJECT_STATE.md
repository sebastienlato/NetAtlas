# Project state

Updated: 2026-10-04. **Phase 10 — Distributed measurement is complete.**
Phase 11 has not started. Package **0.11.0**; control envelope **1**; HTTP schema **1**; local query schema **1**; config **3**;
observation/manifest **2** with explicit v1 reads; fingerprint pack/result schemas
**1**, engine **fingerprints-1**, taxonomy **netatlas-categories-1**; enrichment
bundle/result schemas **1**, engine **enrichment-1**; Alembic head **0005**.

## Delivered

- **Phase 10:** independent authenticated loopback control plane and two local worker
  processes; generated private per-worker credentials stay outside DB/config hashes.
  No UI controls or changes to read authentication; no public/real-input service.
- Migration 0005 adds campaign/job/attempt/worker identities, durable boot fencing,
  leases/heartbeats and persistent global/per-prefix connection pacing. Each dial,
  including TLS, needs a committed one-use 250-ms permit. Delayed grants cannot burst.
- Only unstarted leases can be reassigned (three assignments maximum). Once any permit
  is issued, loss becomes uncertain and never silently remeasures. Restart may recover
  delivery-only authority for the original UUID/digest within 24 hours of claim.
- One fsynced spool slot per worker and bounded retry/backoff provide backpressure.
  Delivery authority, fsynced blobs, source/projection/outbox and acknowledgement receipt
  share one synchronous transaction. Lost acknowledgements replay exact original truth.
- Explicit enabled identity, --measure, --synthetic and literal-loopback scope required
  for enqueue; preview remains offline/default. Existing standalone discovery policy
  is preserved. One active campaign, at most two sockets, 128 pending/1024 retained jobs
  (lab scope itself at most 32). No routed-space/refresh/UDP/global scheduling.
- Cancellation and DB suppression revoke subsequent admission/delivery. Heartbeat loss
  cancels active sockets; already-issued grants/in-flight traffic have documented bounded
  stop latency, not instantaneous physical fencing. Uncertain slots retain their hard
  horizon. Coordinator restart preserves authority/rates; old restores cancel all jobs.
- Worker copies/credentials remain ignored and independently managed; keep boot counters
  on restart, delete/quarantine pending copies for removal, prune control metadata after
  90 days. Read [DISTRIBUTED.md](docs/DISTRIBUTED.md) for commands and precise limits.

- Bounded literal IPv4/IPv6 discovery, pinned policy, exclusions/opt-outs, narrow
  literal-loopback lab mode, shared pacing/queue/deadlines/cancellation, private spool.
  CLI defaults dry-run; enabled operator identity and `--measure` required.
- Opt-in HTTP/TLS/SSH/SMTP evidence: two connections, two GET / requests and one TLS
  handshake per endpoint. No DNS/SNI, redirects, cookies, authentication, mail,
  STARTTLS, crawling or device commands. TCP-open differs from protocol success;
  certificate verification is not performed. No Internet campaign has run.
- Pure offline fingerprints with source/pack/engine/taxonomy provenance and exact
  decoded-byte selectors/hashes. Four core nginx/OpenSSH/Postfix assertion rules;
  other device classes have fictional test coverage only. Unknowns/multiple candidates
  retained; asserted/corroborated confidence is ordinal, not identity proof.
- PostgreSQL 18.3 / PostGIS 3.6.4, SQLAlchemy/psycopg and packaged Alembic. Immutable
  original v1/v2 history, private content-addressed raw blobs, hash-placeholder JSONB
  and evidence_refs reconstruct exact sources. UUID plus canonical digest distinguishes
  replay/conflict; deduplicated bytes never collapse distinct measurement history.
- Fsynced files precede synchronous commits; acknowledgements follow each row's commit.
  One advisory lock coordinates pipeline operations/GC/backup/search. Transactional
  outbox and same-DB consumer receipts support cursor replay; derivation events cover
  fingerprints and enrichment at source granularity. External outbox delivery is not claimed.
- Independent last attempt/open/nonempty-evidence pointers ordered by finish/start/UUID.
  Negative/stale/empty attempts preserve evidence. Synthetic-only local ingestion;
  30-day source expiry, whole-record removal, persistent CIDR suppression, 90-day
  tombstones/removed-source events and 7-day backup policy with tested empty-DB restore.
- Pure offline independent IPv4/IPv6 ASN/city longest-prefix matching, multi-origin
  ASNs, stable-ID gazetteer, unknown/stale/future datasets and explicit uncertainty.
  Checksum-pinned normalized bundles/results retain canonical source/dataset hashes,
  versions, attribution/licenses, matched prefixes and explicit evaluation clock.
- Migration 0003 stores dataset/result snapshots and gazetteer. WGS84 geography points
  and split MultiPolygon boundaries preserve antimeridian behavior and holes; PostGIS
  rejects invalid topology. Replay verifies scalar/spatial projections. Source removal
  cascades; shared snapshots survive until unused.
- Natural Earth v5.1.2 Suva/Fiji public-domain offline demo with **fictional IP/ASN
  associations**. Downloads/generated subsets stay ignored. DB-IP Lite/GeoNames terms
  reviewed, neither imported. No global routing/geo coverage or automatic refresh.
- **Phase 6:** independent `search/` Python module and private `netatlas-search` CLI;
  indexed literal network/port/outcome, product-label text, category, ASN/country/place,
  radius/box/boundary, freshness and current/history filtering. Exact pack/dataset hash
  selection; no arbitrary newest pack, cross-source derivation or stale-match fallback.
- Current attempt/open/evidence is selected before filtering. Actual source expiry and
  suppression apply to all modes; current geography also checks query-time dataset
  validity. Historical as_of cannot resurrect removed sources. Unknown points/radii
  remain unknown; area queries test representative points, not uncertainty-disk overlap.
- Exact unique-endpoint/source/candidate counts, deduplicated category/ASN/prefix/country/
  geography facets, explicit unknowns and bucket truncation. Deterministic ordering,
  bounded pages/offsets/text/areas and 5-second statement timeout. Private metadata
  includes selected dataset attribution/license, source hash and derivation identity.
- Migration 0004 adds nine indexes directly to immutable authoritative tables. No
  asynchronous search copies, separate consumer, raw indexing or eventual deletion lag.
  Reindex, populated upgrades, replay, Phase 4/5/6 backup restore preserve results.
- **Phase 7:** separate typed local read transport with search/facets/places and
  literal endpoint detail/history POST routes. Explicit metadata allowlists exclude
  raw captures, source envelopes, protocol fields and evidence selectors. All labels
  and URLs remain untrusted; transport escaping is not sensitive-data sanitization.
- HMAC query/route-bound keyset cursors, 15-minute lifetime, 10,000-hit traversal cap,
  fixed measurement cutoff and actual retention/implicit-current dataset validity
  rechecks on each page. Live pages are not cross-request snapshots; writes/removals
  can change counts and matches. No cached data can resurrect removed sources.
- Loopback peer/Host/Origin checks, required browser-guard header, no CORS/credentials,
  forwarded-header trust or access logs. Synthetic trusted-local use only. Bounded
  streaming bodies, one in-flight read, 5-second SQL timeout, generic typed errors,
  4 MiB JSON response cap. Health is process liveness, not database readiness.
- Exact dataset-specific place disambiguation, stable IDs/admin/kind/provenance and
  uncertainty; no remote geocoder. Places require a live unsuppressed associated
  source; stale/future bundles return provenance/state with no places.
- OpenAPI-derived TypeScript contract and same-origin cancellable client with drift
  checking in make check. No ingestion route or measurement controls. **OpenSearch is deferred**
  based on the measured local synthetic workload, not assumed global-scale suitability.

- **Phase 8:** responsive React geographic explorer over the actual generated client.
  Exact country/region/city lookup with stable ID/admin/source disambiguation; category,
  product-token, network/ASN, current/history, freshness and geography-state filters.
- MapLibre 6.12.0 clusters only the displayed observation page; full-match endpoint,
  source and candidate counts remain separate. Unknown points/radii, multi-value
  categories/ASNs, facet truncation, live-page clocks and provenance stay explicit.
- Locally bundled worker and reviewed tiny Natural Earth Suva/Fiji assets; offline
  basemap, no external tile/glyph/font/geocoder requests. Explicit `make demo` seed
  creates authored documentation-address fixtures through the real storage pipeline,
  with a time-bound dataset hash printed for explicit UI selection. No auto-seeding.
- Shared cancellable search/place request lane, generation guard, original-query
  continuation, generic error/retry/empty/loading states and traversal-cap notice.
  One displayed page; no persistent/back-page cache. Hidden/pagehide or 60-second-old
  views clear results, places, selected-place metadata and map points. No instant
  server-push removal claim; read-time views revalidate through a fresh request.
- Accessible native controls/list, visible focus, skip navigation, result focus and
  WebGL fallback. Metadata stays inert text with visible control-code tokens; arbitrary
  metadata URLs never become links/resources. Phase 9 inspection is described below.

- **Phase 9:** exact endpoint/source UUID/digest/derivation-bound inspection route,
  with immutable source reconstruction, actual expiry and suppression checks before
  and after projection under the shared storage lock. No arbitrary blob/file reads.
- Separate pure `inspection/` projections expose reparsed protocol fields, bounded
  inert UTF-8 previews, parsed certificate assertions and exact candidate traces.
  Preview policy `synthetic-preview-1` withholds unreviewed headers, SSH comments,
  unsupported/encoded formats and recognized sensitive fields/bodies before truncation.
  2,048-byte body/greeting and 256-byte field limits; controls/bidi made visible.
- Local DER parsing via cryptography 48.0.1 preserves `verification=not_performed`.
  Parsed assertions, failures, unsupported/truncated captures and display/chain
  truncation remain separate. No trust/identity/validity/revocation validation or fetches.
- Selected immutable derivations preserve all ambiguous candidates, ordinal confidence,
  source/rule/pack/engine/taxonomy identity and exact checked byte ranges/hashes.
  Trace excerpts stay withheld; no request runs derivations or combines sources.
- Accessible endpoint timeline and exact observation inspection share the existing
  browser read lane, generation guards, view clearing and 60-second expiry. Timeline
  includes failed/empty attempts, uses original-query continuation and holds one page.
  No captured links/resources/HTML execution, raw download or persistent view cache.

## Architecture and operations

Domain/evidence/observation contracts are I/O-free. Discovery orchestrates policy;
collectors acquire bounded bytes. Fingerprint/enrichment engines are pure and separate.
Storage adapts them under the existing transaction/removal protocol. `search/` depends
on query contracts and the storage connection/lock, never collector execution.
The read API adapts search and source-bound inspection through explicit models; its HTTP response
contract is separate from private dictionaries. The explorer owns only view state;
`netatlas.demo` is a separate explicit operator adapter, never imported by the API.
`control/` owns authenticated worker orchestration; collectors remain independent of
storage and the HTTP control transport.
Read [INSPECTION.md](docs/INSPECTION.md) for the reviewed preview and trace contract.
Read [GEOGRAPHIC_UI.md](docs/GEOGRAPHIC_UI.md) for demo/setup/scope and
[MAP_ASSETS.md](docs/MAP_ASSETS.md) for the deliberately reviewed asset exceptions.

Read [API.md](docs/API.md) for routes, clocks, cursors, cost/access policy and client.
Read [SEARCH.md](docs/SEARCH.md) for exact clocks/counts/filters/limits and
[SEARCH_BENCHMARK.md](docs/SEARCH_BENCHMARK.md) for reproduction and measured results.
Read [STORAGE.md](docs/STORAGE.md), [ENRICHMENT.md](docs/ENRICHMENT.md),
[PROTOCOL_EVIDENCE.md](docs/PROTOCOL_EVIDENCE.md) and [FINGERPRINTS.md](docs/FINGERPRINTS.md)
for inherited contracts. `make db-up COMPOSE=docker-compose` preserves the existing
volume/secret and builds native arm64/amd64 PostGIS from the pinned PostgreSQL base
and direct extension packages; `make db-migrate` applies 0005. Compose-plugin hosts
omit the override. The image context contains only docker/; transitive APT packages
are not fully pinned. Runtime pins are unchanged; Phase 9 adds cryptography 48.0.1
and its locked dependencies for local certificate parsing.

## Verified validation

- Full **make check-db COMPOSE=docker-compose** passed with **348 Python tests,
  26 web unit/component tests and 5 production Chromium tests**. Ruff/format, strict
  mypy, Biome/TypeScript, generated OpenAPI drift, both builds, CLI smoke and existing
  migration/retention/backup/restore acceptance all pass.
- **36 new worker cases** cover authenticated bounded control envelopes, private
  credentials/spools, generations/fencing, lost/reordered registration and claims,
  lease reclaim limits, late delivery and restart, global/per-prefix/IPv6/second-TLS
  admission, occupied socket slots after failure, pacing across coordinator restart,
  clock regression, cancellation/suppression/deadlines, storage backpressure and
  reordered/duplicate delivery with exact source integrity.
- Two actual worker subprocesses used the real HTTP coordinator and PostgreSQL with
  authored HTTP/TLS loopback fixtures. Both lost a delivery acknowledgement and replayed
  without extra probes or outbox events; the TLS endpoint used exactly two connections.
  Killing and restarting a worker during capture left one uncertain attempt and no
  repeated measurement. Heartbeat/cancellation tests verified closure of active sockets.
- Injected failures around blob publication and commit preserve atomic source/job/outbox
  receipts. Missing blobs are never acknowledged; replay cannot revive suppression.
  Populated 0004 upgrade preserves source bytes; restored Phase 10 archives cancel
  historical work before use, while existing older backup acceptance remains passing.
- Python 3.14.7, uv 0.12.19, Node 26.8.1 and npm 11.19.0 verified. Existing dedicated
  Colima netatlas profile, native PostGIS image, volume and secret preserved; operator
  database migrated and verified at **0005**. Credentials, outputs and captures used by
  acceptance stayed in temporary/ignored locations. No real inputs or Internet sweep.
- Read/inspection/UI behavior and inherited browser/Axe acceptance pass unchanged.
  The approximately 1.30-MB main JS / 511-kB worker warning persists. No new global
  throughput, real accuracy, public deployment or physical power-failure qualification.
- No implementation blocker, release or tag. Exact delivery commit, remote HEAD equality,
  clean-tree verification and CI status are reported after publication; reproduce with
  make check-db and the delivery checks in CONTRIBUTING.

### Phase 9 baseline (retained historical record)

- Full **make check-db COMPOSE=docker-compose** passed with **312 Python tests,
  26 web unit/component tests and 5 production Chromium tests**. Ruff/format, strict
  mypy, Biome/TypeScript, generated OpenAPI drift, Python/Vite builds and CLI smoke
  all pass; migrations/retention/backup/restore checks remain included.
- 28 new Python inspection cases cover large/malformed/encoded/hostile inputs,
  redaction before truncation, unverified expired/self-signed certificate assertions,
  exact trace integrity and ambiguity, cross-source rejection, v1/IPv6/negative attempts,
  actual expiry/suppression before cleanup/removal and during projection, generic blob
  failures, immutable replay and noncreating private blob-directory admission.
- Actual stored hostile HTML/certificate fixtures render inertly in production Chromium:
  zero external requests, no injected resource elements or script execution, correct
  trace/protocol/certificate states, keyboard focus and desktop/mobile Axe with no
  violations. Screenshots were inspected. No full assistive-technology audit claimed.
- CI exposed a slower-render focus race; active-view focus now runs only after React
  commits the view, with component and production-browser focus assertions.
- Unit/component checks cover exact inspection requests, original timeline queries,
  late-response rejection, removed-source errors and hidden/60-second evidence clearing.
  Browser outputs are explicitly excluded from source formatting as well as Git.
- Existing Colima profile, PostGIS image, database volume and secret were preserved;
  main migration remains 0004. Build warning remains: 1,300.00 kB main JS (362.11 kB
  gzip), 510.70 kB worker and 91.09 kB CSS. No new capacity benchmark or real inputs.
- No implementation blockers. Preview marker redaction is deliberately incomplete
  for arbitrary sensitive content; synthetic-only use remains mandatory. Delivery
  commit, remote HEAD equality, clean-tree and CI status are reported after publication.

### Phase 8 baseline (retained historical record)

- Full **make check-db COMPOSE=docker-compose** passed with **284 Python tests,
  22 web unit/component tests and 4 Chromium production-browser tests**. Ruff/format,
  strict mypy, Biome/TypeScript, OpenAPI drift, Python/Vite builds and CLI smoke pass.
  Existing migrations/retention/backup/restore acceptance remains included. The main
  database was migrated/verified at 0004; its existing volume and secret were preserved.
- Browser tests use the real API, actual generated client and isolated PostgreSQL seed.
  Representative country/region/city, same-name places, category/source selection,
  unknowns/radii, pagination, actual clusters, keyboard/mobile layout, hostile content,
  generic error recovery and WebGL fallback pass. Zero external browser requests in
  the end-to-end search flow; desktop/mobile Axe reported no violations. Screenshots
  were inspected; this is not a comprehensive assistive-technology certification.
- Unit tests cover original-query continuation for search and places, stale/late results,
  cross-route serialization/cancellation, field invalidation, control characters,
  provenance URLs, display/selection expiry, error codes and limits. New DB seed tests
  verify fixture truth, geometry equality and suppression/removal through real storage.
- MapLibre worker bundling was verified in Vite development and production preview.
  The large bundle warning remains: about 1.29 MB main JS (359 kB gzip), 511 kB worker,
  91 kB CSS; no low-bandwidth performance qualification. Test output remains ignored.
- Runtime pins remain Python 3.14.7, uv 0.12.19, Node 26.8.1 and npm 11.19.0;
  PostgreSQL 18.3/PostGIS 3.6.4 on the existing dedicated Colima runtime.

### Phase 7 baseline (retained historical record)

- Full **make check-db COMPOSE=docker-compose** passed with **282 Python and 6 web
  tests**: 42 new API acceptance cases, all prior search/storage migration/restore
  tests, Ruff/format, strict mypy, Biome/TypeScript, OpenAPI client drift, Python/Vite
  builds and offline CLI smoke. The local PostgreSQL/PostGIS volume and secret were
  preserved; make db-migrate remains at 0004.
- API tests compare route results against authored search truth for text/category/
  ASN/places/radius/box/boundary/unknown/freshness/history. They cover IPv6 endpoint
  detail/history, same-name places, stale/future bundles, missing radii, ambiguity,
  ties/late inserts, cursor query/route/restart/lifetime binding and traversal caps.
- Read-time suppression before cleanup, removal/replay and actual expiry exclude
  data, including historical queries and continuations. Current dataset expiry is
  rechecked on continuation. Hostile labels/URLs stay escaped JSON; raw bytes are
  excluded, blob/DNS/measurement entry points are forbidden during the acceptance
  read, and importing the API loads no discovery/collector module.
- Streamed body/depth/size limits, loopback/Host/Origin policy, generic errors,
  one-request admission, a real PostgreSQL statement timeout and response size cap
  are tested. The TS client tests same-origin paths, IPv6 encoding, AbortSignal,
  omitted credentials, redirect refusal and generic failures.
- A real loopback HTTP smoke verified Phase 7 health, a bounded stored-data read,
  no-store headers and cross-origin rejection; the temporary listener was stopped.

The Phase 6 benchmark remains the search workload reference; this phase does not
claim a new capacity benchmark.

### Phase 6 baseline (retained historical record)

- Full **`make check-db COMPOSE=docker-compose`** runs the required complete `make
  check` with PostgreSQL enabled: **240 Python and 3 web tests**, Ruff/format, strict
  mypy, Biome/TypeScript, Python wheel/source and Vite builds, plus offline CLI smoke.
  Plain `make check` skips DB integration without `NETATLAS_TEST_DB=1`; CI requires it.
- 28 search cases compare authored exact truth for ambiguity/multi-origin ASNs,
  IPv4/IPv6, current/history/freshness, selected pack/dataset identities, stale/future
  datasets, missing geography/radius, same-name places, antimeridian/radius/boundary
  areas/holes/edges, ordering/pagination, query/input/output bounds and generic errors.
- Search tests verify no raw-blob reads, read-time suppression before cleanup, expiry
  without maintenance even with historical as_of, replay/removal, REINDEX, populated
  0003 upgrade and Phase 5/6 restore equivalence. Existing 0001/0002 upgrade, Phase 4
  restore, durable pipeline, collector and offline derivation checks remain passing.
- Reproducible synthetic benchmark: 2,048 endpoints, 6,144 observations, 20 warm measured
  samples/query after warm-up, exact facets/counts included; nine added indexes 7.93 MiB. Final timings and actual unforced index plans are summarized in the benchmark
  document; full generated plans remain ignored. No Internet measurement or real input.
- Host: Apple M4 Max / 64 GiB, macOS arm64; dedicated Colima netatlas 2 CPUs / 2 GiB /
  20 GiB disk. Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0; PostgreSQL 18.3 /
  PostGIS 3.6.4. Toolchain and database availability verified this phase.

Private repository: https://github.com/sebastienlato/NetAtlas; delivery branch `main`.
The completion report and Git/Actions identify exact commit/push/CI status; this
file cannot contain its own final hash. Verify local HEAD against
`git ls-remote origin refs/heads/main` and confirm empty `git status --porcelain`.

## Limitations and blockers

No Phase 10 implementation blocker. No raw download, real-data ingestion,
comprehensive sensitive-content sanitizer, public authentication, production
role isolation, encrypted backup, worldwide workers, release or tag exists.
The new authenticated control plane is trusted-local and uses only literal-loopback
fixtures. Authentication trusts provisioned workers; it does not sandbox hostile code.
Local query dictionaries/offsets remain private; HTTP uses separate Phase 7 models. Labels remain
untrusted; hashes do not authenticate peers or dataset publishers.

Exact broad aggregates scale with matched rows. One lock serializes operations;
benchmarks are small, local, warm-cache and single-client, not production/concurrent
capacity or global prevalence. All statistics describe selected retained observations,
with category ambiguity, protocol/vantage/IPv6/retention/geographic coverage bias.
No real-world precision/recall, geography accuracy or worldwide completeness is claimed.
The offline basemap covers Fiji only. The UI shows at most one 200-item page, not
whole-database geographic clusters, and offers no arbitrary as_of/radius/box editor.
The complete accessible list works if WebGL is unavailable.

Bundles remain bounded to 2 MiB / 4096 rows per collection, using linear prefix lookup.
Only a normalized local format and tiny pinned Natural Earth converter exist; no global
routing/geolocation importer, downloader, paid service or automatic refresh. Dataset
rights and validity windows require operator review. Missing radius means unknown;
country/generalized polygons are not legal boundaries or device-location evidence.

Historical queries use retained measurements through as_of and selected derivation
identities, not ingestion-time knowledge snapshots. Actual source retention/suppression
always wins. Local CLI offset pages can change across requests; deep offsets stop at 10000.
HTTP keysets bound traversal to 10000 hits and also use a live view; see API.md. No current result
silently combines older evidence with a newer source's fields.

Expiry/GC are explicit commands. Old restores need current suppressions before use;
spools, datasets, offline/search outputs and backups require separate removal. Keep
backups at most 7 days. Trusted OS/container/DB owners retain access. Removal replay
horizon is 90 days; external consumers need coordinated deletion contracts. Power-loss,
failover, distributed throughput and production durability remain unqualified.

## Next

**Phase 11 — Coverage and refresh scheduling**, in a fresh chat using [docs/NEXT_PHASE.md](docs/NEXT_PHASE.md).
Do not begin Phase 11 in this Phase 10 chat.
