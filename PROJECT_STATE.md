# Project state

Updated: 2026-10-04. **Phase 5 — Network and Geographic Enrichment is complete.**
Phase 6 has not started. Package **0.6.0**; config **3**; observation/manifest **2**
with explicit v1 reads; fingerprint rule-pack/result schemas **1**, engine
**fingerprints-1**, taxonomy **netatlas-categories-1**; enrichment dataset/result
schemas **1**, engine **enrichment-1**; Alembic head **0003**.

## Delivered

- Bounded literal IPv4/IPv6 discovery, pinned policy, exclusions/opt-outs, narrow
  literal loopback lab mode, shared pacing/queue/deadlines/cancellation, private spool.
  CLI defaults dry-run; enabled operator identity and `--measure` required.
- Opt-in HTTP/TLS/SSH/SMTP evidence within two connections, two GET / requests and
  one TLS handshake per endpoint. No DNS/SNI, redirects, cookies, authentication,
  mail, STARTTLS, crawling or state-changing interactions. TCP-open is distinct
  from protocol success; TLS certificate verification is not performed.
- Pure offline fingerprints with source/pack/engine/taxonomy provenance and exact
  decoded-byte selectors/hashes. Core pack has four nginx/OpenSSH/Postfix assertion
  rules; other device classes have fictional test coverage only. Unknowns/multiple
  candidates retained; asserted/corroborated confidence is ordinal, not identity proof.
- PostgreSQL 18.3 / SQLAlchemy / psycopg / packaged Alembic, immutable original
  v1/v2 history, private content-addressed evidence and separate fingerprint results.
  UUID plus canonical digest distinguishes replay from conflict; distinct measurement
  history survives blob deduplication. Fsynced files precede synchronous DB commit;
  per-row acknowledgements follow commit. Internal hash placeholders/evidence_refs
  reconstruct original source envelopes without a wire-schema rewrite.
- Independent last attempt/open/nonempty-evidence pointers ordered by finish/start/UUID.
  Negative/stale/empty arrivals preserve prior evidence. Global local advisory lock
  coordinates reads, writes, GC and backup. Transactional outbox and idempotent
  same-DB consumer/receipts support cursor replay without external delivery claims.
- Synthetic-only local ingestion; 30-day source expiry, whole-record removal,
  persistent CIDR suppression, 90-day tombstones/removed-source events, private
  loopback storage, 7-day backup policy and verified empty-DB restore.
- **Phase 5:** bounded checksum-pinned normalized offline datasets, independent
  IPv4/IPv6 ASN/city longest-prefix matching, multi-origin ASN tuples, explicit
  unknown/stale/not-yet-valid results, provider-radius uncertainty and stable-ID
  gazetteer with same-name alternatives. No inferred nearest city or device location.
- Separate deterministic enrichment results link source hash, dataset ID/version/hash,
  engine/schema, explicit UTC evaluation time and all origin/license/attribution
  metadata. Same-version content changes remain distinguishable. Original observations
  and embedded legacy placeholders are never rewritten.
- Migration 0003 adds PostGIS 3.6.4, immutable enrichment snapshots/results and
  dataset-specific gazetteer. WGS84 geography points support metre distances;
  MultiPolygon geometry boundaries retain holes and antimeridian splits. PostGIS
  rejects invalid topology. No search workload indexes or geographic query API.
- Enrichment shares existing transaction/outbox semantics. Replay verifies snapshots,
  results and typed/spatial projections. Source removal cascades; unused snapshots
  and gazetteer rows are removed while shared snapshots survive. Backup/restore
  includes spatial data and upgrades older Phase 4 archives before verification.
- Public-domain Natural Earth v5.1.2 Suva/Fiji offline demonstration, pinned original
  source hashes and attribution, **fictional documentation-IP/ASN mappings**. Actual
  downloads/generated subsets stay ignored; committed fixtures are authored synthetic.
  DB-IP Lite/GeoNames terms reviewed; neither dataset imported. No account/paid service.
- API health and web shell now describe Phase 5; they expose no stored observations,
  geographic search, map, ingestion route or measurement controls.

## Architecture and operations

Domain/evidence/observation contracts are I/O-free. Discovery orchestrates policy;
collectors acquire bounded bytes. Fingerprint and enrichment engines are pure and
independent of collection. `enrichment/offline.py` and `demo.py` bound local files;
URLs are inert metadata. `storage/enrichment.py` adapts pure results to PostgreSQL;
collectors/API/UI do not import storage or initiate enrichment/measurement.

Read [ENRICHMENT.md](docs/ENRICHMENT.md) for exact contracts, limits, license review,
source hashes and the complete offline demonstration. Read [STORAGE.md](docs/STORAGE.md)
for private setup, durability/removal/restore and Phase 4 upgrade procedure.
`make db-up COMPOSE=docker-compose` builds the local native arm64/amd64 image from
the unchanged PostgreSQL 18.3 multi-platform digest plus pinned PostGIS server/scripts
3.6.4 packages; `make db-migrate` applies 0003. Compose-plugin hosts omit the override.
Keep existing volume/secret. The Docker build context contains only `docker/`.

`netatlas-enrich` inspects bundles, disambiguates exact place names and writes offline
results. `netatlas-store enrich` accepts an existing source UUID plus dataset/file
checksum/evaluation time. `verify` now includes an `enrichments` count. `derivation`
outbox events cover both fingerprint and enrichment changes at source granularity.

## Verified validation

- Full Phase 5 **`make check-db COMPOSE=docker-compose` passes 212 Python tests and
  3 web tests**, Ruff/format, strict mypy, Biome/TypeScript, Python wheel/source and
  Vite builds, plus offline CLI smoke. This runs the required complete `make check`
  with `NETATLAS_TEST_DB=1`; plain `make check` otherwise skips database tests.
- 29 offline enrichment tests plus 53 total storage tests cover prefix boundaries,
  IPv4/IPv6 independence, unknowns, multi-origin ASNs, stale/future validity, exact
  replay, v1 preservation, unchanged source bytes, version/hash changes, invalid
  datasets/checksums/IDs/geometry structure, no-network engine, same-name places,
  source attribution, private no-clobber output and no partial output on failure.
- Real PostgreSQL/PostGIS acceptance covers spatial projections and metre thresholds
  across the antimeridian, topology rejection, immutable UPDATE rejection, rollback
  and lost acknowledgement, tamper detection, shared-snapshot expiry/suppression,
  populated 0001/0002 upgrades, Phase 4 archive migration and Phase 5 spatial restore.
  Existing durable pipeline/collector/fingerprint checks remain passing.
- Manual demo: pinned Natural Earth files converted to a small private bundle;
  synthetic IPv4 source enriched offline and in storage, Suva/Fiji projections
  persisted and independent replay passed. The installed enrichment CLI and a spatial
  backup/restore drill also passed; wheel contents include the engine and migration.
  Only authored documentation addresses
  and existing loopback fixtures were used. No Internet campaign or real ingestion.
- Runtime pins unchanged: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0.
  No Python/web dependency additions. Local PostGIS reports 3.6.4 on PostgreSQL 18.3.
  The existing Colima profile was restarted and a pre-upgrade backup preserved.
- CI continues to require full `make check-db` on Linux. Git history and Actions
  identify exact final delivery and CI status; historical counts are not future checks.

Private repository: https://github.com/sebastienlato/NetAtlas; delivery branch `main`.
Verify `git rev-parse HEAD` against `git ls-remote origin refs/heads/main` and confirm
empty `git status --porcelain`. The completion report identifies the final commit.

## Limitations and blockers

No Phase 5 implementation blocker. No real-data ingestion, public raw display,
field-level sanitizer, production role isolation, encrypted backups, authentication,
search infrastructure, stored-data API, geographic UI, distributed workers, release
or tag exists. Source/derivation hashes do not authenticate peer or publisher claims.
No real-world precision/recall, geography accuracy or worldwide coverage is claimed.

Enrichment is bounded (2 MiB bundles; 4096 rows per collection), with linear prefix
lookup. Only the normalized local format and a tiny pinned Natural Earth converter
are implemented. No global routing/IP geolocation importer, downloader, service,
automatic refresh or comprehensive gazetteer exists. The demo's IP/ASN associations
are fictional. Its October 2026 validity window is a test policy, not upstream release
freshness. Dataset URLs/rights/validity metadata require operator review.

IP geography describes approximate area context, never a precise person/device.
Missing radii remain unknown. Offline geometry checks structure/bounds/splitting;
full topology is checked on PostGIS insertion. Generalized country boundaries are
not survey/legal boundaries. Historical replay uses recorded evaluation time;
**future current queries must check dataset expiry at the query clock** as well as
source expiry, retaining uncertainty and version identity.

Expiry/GC are explicit operator commands, not jobs. Old restores require current
suppressions before use. Downloaded datasets, offline results, spools and backup
copies need separate removal. Keep backups at most 7 days. OS/container admins and
the DB owner remain trusted. One lock favors correctness over throughput; outbox
atomicity covers same-DB handlers only. Removal event/tombstone replay horizon is
90 days; external consumers require coordinated deletion semantics. Physical power
loss/failover and production durability/throughput have not been qualified.

The PostGIS build pins its base and direct extension packages, not every transitive
APT package; rebuilds are not bit-identical. Missing pinned packages require a
reviewed update. No automatic upgrade or change to local credentials/volume occurs.

## Next

**Phase 6 — Search and Aggregate Statistics**, in a fresh chat using
[docs/NEXT_PHASE.md](docs/NEXT_PHASE.md). Do not begin it in this Phase 5 chat.
