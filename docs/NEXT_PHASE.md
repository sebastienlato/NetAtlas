# PHASE 8 — FRESH WORK CHAT KICKOFF

You are the authoritative developer and project manager for NetAtlas — Global
Internet Exposure Search & Visualization, an independent university thesis project.
Complete exactly Phase 8 in this fresh Work chat; do not begin Phase 9.

Read AGENTS.md, PROJECT_STATE.md, README.md, ROADMAP.md, ARCHITECTURE.md, DECISIONS.md,
CONTRIBUTING.md, SECURITY.md, docs/API.md, docs/DATA_MODEL.md, docs/STORAGE.md,
docs/ENRICHMENT.md, docs/SEARCH.md, docs/SEARCH_BENCHMARK.md, docs/DISCOVERY.md,
docs/PROTOCOL_EVIDENCE.md and docs/FINGERPRINTS.md first. Inspect Git status/remotes,
toolchains, code/tests and the existing web shell/client. Repository files are
authoritative. Respect user changes and make routine engineering decisions
autonomously without approval gates.

Phase 7 delivered package 0.8.0, HTTP and local query schemas 1, Python 3.14/FastAPI/
Pydantic and a React/TypeScript/Vite shell with an OpenAPI-derived read client.
Config 3; observation/manifest 2 with explicit v1 reads; fingerprint pack/result 1,
engine fingerprints-1, taxonomy netatlas-categories-1; enrichment bundle/result 1,
engine enrichment-1; Alembic head 0004. PostgreSQL 18.3/PostGIS 3.6.4 with SQLAlchemy/
psycopg. No geographic UI, evidence viewer, public deployment or Internet campaign
exists. OpenSearch remains deferred by the small local synthetic benchmark.

Implement Phase 8 — Geographic exploration UI: country/region/city place search,
results list and MapLibre clusters, categorized filters, accessible navigation and
an offline demonstration map. Acceptance includes representative end-to-end searches,
responsive layout, same-name place disambiguation, attribution and uncertainty,
and loading/error/empty states. Use the actual Phase 7 API/client; keep UI, API,
search, storage, domain and collectors separable. Make necessary bounded integration
adjustments transparently, preserving contracts and testing any changes. Do not build
Phase 9 protocol/certificate/raw-evidence inspection or expand collection.

Read API routes are POST /api/v1/search, /facets, /places and
/endpoints/{address}/{transport}/{port}/detail or /history. JSON requires explicit
schema_version:1, query and optional cursor; Content-Type application/json and
X-NetAtlas-Read:1. The header is a browser guard, not authentication. Same-origin Vite
proxying, literal loopback socket peers, approved local Host/Origin values, disabled
forwarded trust/access logs and no CORS/credentials are the local synthetic access
policy. Do not expose or proxy the service publicly. /healthz is process liveness,
not database readiness. The static example route is explicitly synthetic.

Use web/src/api/client.ts and its generated schema.ts. Regenerate with
uv run --locked python -m netatlas.read_api.contract after deliberate contract edits;
make check rejects OpenAPI drift. Types are compile-time contracts, not runtime JSON
validation. The client supports AbortSignal, omits credentials, refuses redirects and
uses same-origin paths. Cancel stale UI requests and prevent outdated results from
replacing newer selections. Handle the documented generic errors, 429 busy, unavailable
storage, expired/invalid cursors and response/page limits. No automatic target lookup,
scan, DNS, dataset download or enrichment execution may follow a UI action.

Current attempt/open/evidence is selected BEFORE filters; no older-match fallback.
History selects retained sources. Exact pack hash defaults to core; dataset hash
must be explicitly chosen, otherwise enrichment is disabled. Engine/taxonomy identity
and latest evaluation at/before as_of remain explicit. Do not invent newest-dataset
selection or mix sources/derivations. Product text is simple-token AND over labels,
not raw evidence. Preserve unknowns, ambiguity and multiple ASNs/categories.

Counts distinguish endpoint keys, source observations and all selected candidates.
Facets deduplicate per source/endpoint, include their own filter, and report bucket
truncation. History/multi-value buckets can exceed totals. These are selected retained
observations, not physical devices or Internet prevalence. Do not present page-only
MapLibre clusters as whole-database exact geographic aggregates. Search pages are
bounded; define and label the map's loaded-result scope and any truncation clearly.

Search/history cursors use finish/start/UUID keysets, signed route/query binding,
15-minute nonrenewing lifetime, process-local signing keys and a 10000-hit cap.
Resubmit the ORIGINAL request query with next_cursor, not the expanded response
selection. Changing filters restarts pagination. Restarting the API invalidates old
cursors. Pages are live retained-data views, not cross-request snapshots: writes,
derivations, expiry/removal can change totals/matches. No client cache may defeat
removal/retention. Measurement cutoff/freshness reference is pinned; actual retention
and implicit-current dataset validity are rechecked every page. Explicit historical
as_of cannot resurrect expired/suppressed/deleted sources.

HTTP limits: 16 KiB JSON, depth 32, five-second body deadline, 256-character text/name,
1–200 hits/places, 1–50 buckets per facet, 2048-character cursor, four-MiB response,
one in-flight data request, five-second SQL timeout and ten-second shared-lock wait.
HTTP offset must be zero. Coordinate concurrent UI requests to respect the single
read slot. Exact broad counts can time out. Keep error messages generic and never
log full queries, raw captures or credentials.

Places require an exact dataset hash and use exact casefolded name/country/kind
filters with stable-ID continuation. Names are not identities; preserve admin code,
kind and source ID in disambiguation. A dataset needs a live unsuppressed associated
source to appear in this route. Stale/future datasets return provenance/state without
places. Gazetteer entries are not observation counts. Full boundary coordinates are
not exported; search supports boundary filtering by stable place ID. If map needs
geometry, prefer a small licensed offline basemap/fixture, and keep scope bounded.

Geography means approximate representative points, never a precise person/device.
Missing accuracy radius remains unknown, not zero. Radius/box/boundary queries test
points, not provider-uncertainty-disk overlap. Preserve antimeridian behavior and
polygon holes. Do not infer verified country membership. Retain dataset/pack versions,
source hashes, attribution/licenses, validity and matched-prefix/radius metadata.
Natural Earth v5.1.2 Suva/Fiji is the small public-domain demo with fictional
documentation-IP/ASN mappings; DB-IP Lite/GeoNames were reviewed but not imported.
No global routing/geolocation coverage, paid provider, downloader or refresh exists.
Do not treat public OSM tile servers as a bulk-download CDN. Keep the demo usable
without paid services or external tile/network requests; record asset licenses.

API response fields are allowlisted metadata, not a sensitive-content sanitizer.
No raw blob, source envelope, protocol headers/body/certificate, contact metadata or
evidence selector is exposed. JSON escapes controls/non-ASCII/HTML delimiters; decoded
strings and provenance URLs remain hostile. Render inert text, visibly handle controls
where needed, and never inject HTML, embed remote resources or auto-link arbitrary
metadata URLs. Keep real ingestion prohibited. Evidence inspection is Phase 9.

Storage retains immutable original v1/v2 sources in private raw blobs and hash-placeholder
JSONB/evidence_refs; independent derivation snapshots are replayable. Source UUID plus
digest distinguishes replay/conflict; history survives deduplication. Fsynced blobs
precede synchronous commits; acknowledgements follow each row. One advisory lock
covers writes, reads, maintenance, GC and backup. Current pointers independently
order attempt/open/nonempty-evidence by finish/start/UUID; negative/empty attempts
preserve evidence. Transactional outbox and same-DB receipts support replay; migration
0004 indexes authoritative rows directly, without asynchronous deletion lag.

Sources expire after 30 days. Reads reject expiry; explicit maintenance removes
history/derivations/projections and unused snapshots/blobs. Persistent CIDR suppression
blocks ingestion and removes matching records. Tombstones/removed-source events last
90 days. Spools/downloads/offline/search outputs/backups need separate removal. Backup
policy is seven days; old restores need current suppressions before use. Never delete
existing volumes/secrets to restart local development. No production role isolation,
encrypted backup, distributed workers, release or tag exists.

Discovery remains disabled/dry-run by default, with enabled identity plus --measure
required; protocol evidence additionally needs measurement.protocol_evidence=true.
Only literal IPv4/IPv6/small CIDRs, pinned policy, exclusions/opt-outs and shared
budgets are supported; lab mode permits literal 127.0.0.1/::1 only. Maximum two
connections, two GET / requests and one TLS handshake per endpoint. No DNS/SNI,
redirects/cookies/authentication/mail/STARTTLS/crawling/device commands. Never add
credential guessing, bypass, exploitation, persistence, remote modification or
Internet smoke targets. Use synthetic/loopback fixtures only.

Runtime pins: Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0. TLS tests need
OpenSSL/ephemeral keys. Dedicated Colima netatlas may need restarting; inspect Docker/
Compose first. Run make db-up COMPOSE=docker-compose and make db-migrate; plugin
hosts omit the override. Native arm64/amd64 PostGIS preserves the existing PostgreSQL
base/volume/secret and pins direct extension packages, not every transitive APT package.
Phase 7 passed 282 Python and 6 web tests, strict checks, contract drift, both builds,
CLI smoke and DB migration/backup/restore acceptance. Verify current results.

At completion run meaningful UI/end-to-end/accessibility/hostile-content checks and
make check-db (full make check with PostgreSQL integration enabled). Review tracked
files/diff for secrets, raw captures, datasets and generated outputs; commit only
appropriate code/docs and deliberately reviewed small synthetic/demo assets. Update
authoritative docs with actual results/limits and replace NEXT_PHASE with a complete
Phase 9 kickoff. Commit with a Phase 8 message, push if a remote exists, verify local
HEAD equals remote delivery HEAD and a clean tree, inspect CI, report checks/commit/
push/blockers/current state and the full Phase 9 kickoff, then stop. No release/tag.
Ask only for genuine blockers, credentials, permissions or unavoidable manual actions
after completing independent authorized work.
