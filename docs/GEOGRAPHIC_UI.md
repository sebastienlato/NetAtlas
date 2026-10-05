# Phase 8 — geographic explorer

Package 0.9.0 replaces the empty web shell with an accessible local explorer over
the actual schema-1 read client. No query contract, storage migration, collector,
raw-evidence route or measurement policy changed. Alembic remains 0004. Health
now reports Phase 8; the OpenAPI-derived client digest was regenerated accordingly.

## Local offline demonstration

Install locked dependencies once (`make setup`); browser checks additionally require
`npm --prefix web exec -- playwright install chromium` (CI adds `--with-deps`).
With the existing private local database and credentials:

```sh
make db-up COMPOSE=docker-compose
make demo
make dev-api
# In another terminal:
make dev-web
```

Open `http://127.0.0.1:5173`. Paste the **dataset_sha256 printed by make demo** into
Dataset SHA-256, then Search observations. The hash explicitly selects that snapshot;
blank disables enrichment. Blank fingerprint hash selects core. The seed is an
explicit local operator action, never a browser/API action. It runs normal expiry
maintenance, then appends 13 authored sources for 12 documentation-address endpoint
keys, derives the core pack and enriches with the reviewed tiny packaged geography.
It preserves existing volumes, credentials and unexpired owner data. Repeating the
seed appends new source history and a new time-bound dataset; it is not an idempotent
reset. Persistent suppressions still reject input. No targets are contacted.

The demo's dataset is valid from seed time minus one day through seed time plus
seven days. These are **authored demonstration windows**, not a provider release or
accuracy claim. Sources retain the ordinary 30-day expiry. Rerun the explicit seed
for a fresh demo and select its newly printed hash. Normal maintenance removes old
sources and unused snapshots; downloaded files and other output copies remain
separately managed. The map itself works without a database; search needs local API
and PostgreSQL. After dependency/browser setup, demo execution needs no Internet,
paid account, tile server, geocoder, font service or additional dataset download.

Representative searches in an otherwise empty demo database:

- Default attempt: 12 endpoints, 12 source observations, 10 candidates; 11 mapped
  points and one unknown. A negative follow-up for 192.0.2.1 preserves older evidence.
- Product `nginx` + web-server category: six current attempts; choose last nonempty
  evidence for seven. These are banner assertions, not verified software/device identity.
- Find `Suva` (city) and select `ne:1159150917`: nine current sources.
- Find `Fiji` (country): 11 country-code associations. Optional generalized-boundary
  matching tests points and can yield different counts; it proves no country membership.
- Find `Example Region` (region): the default synthetic boundary yields 10 points.
  Region boundaries are explicit and never inferred from names/admin text.
- Find `Example Harbor` (city): two distinct IDs, `demo:east` and `demo:west`, with
  different admin codes but the same name/country. Select west for 192.0.2.10 and its
  fictional 250-km provider radius. Other mapped demo radii remain unknown.
- All retained mode includes 13 sources. Five-item pages exercise signed continuation.
  IPv6 literal filtering and geography-unknown selection use the same API semantics.

## Interaction, scope and retention

Place lookup uses exact casefolded names, optional country/kind, an exact dataset
hash, stable IDs and 50-entry continuation. Gazetteer entries are not observation
counts. Stale/future datasets show state/provenance with no selectable places.
Country selection uses the dataset country code; city/region association uses stable
place ID unless an available boundary is explicitly selected (default for regions).
No boundaries are downloaded from the API. The UI preserves IDs, kinds, admin codes,
origin IDs and unknowns in the disambiguation labels.

The search form exposes product-token AND, category (all taxonomy IDs), literal
network, ASN, country, current attempt/open/evidence, current/all-retained mode,
24-hour freshness, geography state, exact pack/dataset hashes and 5–200 item pages.
It does not yet provide arbitrary as_of, radius, box, port or outcome editors, though
those remain available in the unchanged API. No service timeline, raw capture,
certificate or confidence/evidence trace viewer is part of Phase 8.

One request lane coordinates search and places; search responses already contain
facets, so the UI sends no redundant concurrent facets read. AbortSignal cancels
obsolete work and generation checks reject late responses. Jobs queue behind the
settlement of an aborted fetch. A server may still be completing that read; generic
429 busy invites an explicit retry, never an unbounded automatic retry loop.
Filters invalidate pages immediately. Continuation resubmits the **original query**,
not expanded selection metadata. Expired/restarted cursors offer a fresh search.
Response/body limits invite smaller pages or narrower filters; unavailable storage,
timeouts, empty results and loading/cancel states are distinct.

Only one result page is displayed and held in memory. Next-page reads replace it;
there is no back-page cache, result accumulation, local/session storage, service
worker or offline observation archive. Hidden/pagehide and 60-second display expiry
clear results/places/selected-place metadata/map points and cancel pending reads. A displayed page remains
a read-time view for at most 60 seconds; there is no push deletion notification or
instant removal claim. Refresh obtains new retained truth. Browser back navigation
cannot restore an application result cache. Retention/suppression is checked by the
API every read; no UI action reconstructs or revives deleted sources.

The map uses MapLibre GeoJSON clustering over usable **displayed-page observation
points** only, capped by the selected page size. Counts on clusters are observation
counts, not endpoint/device counts or full-database geographic aggregates. Unknown,
stale and future points are not mapped. The map/list scope and unmapped count are
always visible; API traversal-cap and facet-bucket truncation have explicit notices.
History and multi-valued facet totals may exceed endpoint totals. Exact full-match
endpoint/source/candidate counts stay separate from the map scope.

Points near the antimeridian are fitted together without a world-spanning box;
source polygons retain their split geometry. Basemap coverage is **Fiji only**;
empty surrounding map is not a claim of ocean or absent observations elsewhere.
Missing radii remain unknown; no precision circle is invented. Area predicates test
representative points, not uncertainty-disk overlap. No verified physical identity,
country membership, geolocation accuracy, global coverage or prevalence is asserted.

## Rendering and access

All metadata stays React text; Cc/Cf/line/paragraph control code points become visible
`[U+XXXX]` tokens. Provenance URLs are text, never arbitrary links or embedded
resources. Map features receive only a source ID and controlled category; no metadata
HTML enters MapLibre. Cluster counts use textContent. The fixed local MapLibre
license link is authored application content. The stylesheet uses system fonts.
No map glyph, sprite, tile, telemetry, geolocation or provider request is configured.

Keyboard-accessible native controls, visible focus, skip navigation, status/error
announcements and the complete result list supplement the map. Map point clicks
focus the matching card; each mapped card can locate its point. Native cluster
buttons zoom; controls honor reduced motion (programmatic motion is instantaneous).
No map interaction is required to search, select a place or read all results.
If WebGL/worker rendering fails, the list remains available with a generic notice.

The listener/proxy policy remains literal loopback, approved local Host/Origin,
X-NetAtlas-Read browser guard, omitted credentials, no redirects/CORS/forwarded trust
and disabled access logs. Do not forward the local API/web server publicly. Metadata
allowlisting and inert display are not sensitive-content sanitization or real-input
authorization; ingestion remains synthetic only.

## Implementation and acceptance

`App.tsx` owns forms, page state and original query/cursor identity. `explorer/model.ts`
owns view-only formatting, map conversion and the request lane; `Map.tsx` owns local
MapLibre presentation; `Metadata.tsx` owns list/provenance rendering. The generated
client remains the only stored-data transport. `netatlas.demo` is a separate explicit
operator seed module; the API never imports or invokes it.

MapLibre 6.12.0's module worker is explicitly bundled with Vite's `?worker&url` so
development optimization and production output both resolve it locally. The
production build includes approximately 1.29 MB main JavaScript (359 kB gzip), a
511 kB worker and 91 kB CSS before gzip; Vite reports its normal large-chunk warning.
This phase qualifies correctness, not low-bandwidth/mobile performance or scale.

`make check-db COMPOSE=docker-compose` runs all checks plus browser acceptance.
The browser fixture creates a uniquely named disposable PostgreSQL database, seeds
through the real pipeline, serves the actual API on loopback and uses the production
Vite build/preview on port 5173. It drops only its own database and temporary blobs
on normal shutdown; it never replaces the operator database. Keep those ports free.
Abrupt host/process loss can leave its identifiable `netatlas_test_web_*` database.

Browser checks exercise country/region/city, same-name disambiguation, category and
source selection, unknowns/radii, continuation, real clusters, desktop/mobile layout,
keyboard focus, zero external requests, hostile labels/URLs, recoverable errors and
WebGL fallback. Axe scans desktop/mobile; this is automated coverage, not a full
assistive-technology audit. Component tests add delayed noncooperative responses,
cross-operation serialization, controls, stale place states, display expiry and
all important generic failure paths. Existing API/PostGIS tests remain authoritative
for suppression, actual expiry, source-choice ordering, polygon holes and area truth.

Asset source hashes, selection procedure and licenses are in [MAP_ASSETS.md](MAP_ASSETS.md).

## Phase 9 integration

The existing map/search behavior is preserved. Result cards now open an all-attempt
endpoint timeline or exact observation inspection. Both use the shared request lane
and replace the previous view, with the same hidden/pagehide/60-second clearing.
Keyboard focus and the skip link target the active view. See [INSPECTION.md](INSPECTION.md)
for protocol/certificate/trace contracts and preview limitations. Package is now
0.10.0 and health reports Phase 9; the original operator seed remains unchanged.
