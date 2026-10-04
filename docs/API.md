# Local read API — through Phase 8

Package 0.9.0 retains HTTP schema 1 over the Phase 6 search engine and synthetic
PostgreSQL storage. No migration is required: Alembic head remains 0004. No request
can initiate measurement, resolve targets, download datasets, derive new records,
read raw blobs or change stored data. The Phase 8 geographic explorer is documented in GEOGRAPHIC_UI.md; evidence
inspection remains Phase 9. This is a local operator demonstration, not a public service.

## Start and access

Run `make db-up COMPOSE=docker-compose`, `make db-migrate`, then `make dev-api`.
Compose-plugin hosts omit the override. Reuse the existing private volume and secret.
The API lazily opens `data/storage` connection settings; unavailable/unmigrated
storage returns generic 503 errors. `/healthz` reports process liveness, version
and Phase 8, not database readiness. `/api/v1/examples/observation` remains an
explicit authored static example, independent of database retention.

Only literal socket peers 127.0.0.1/::1 and Host names 127.0.0.1, [::1], localhost
are admitted. Allowed Host ports are the configured API port, 5173, or omitted.
The supplied launcher disables forwarded-header trust and access logs. Origin,
when present, must be an HTTP loopback origin on the configured API port or 5173;
null and other origins fail. Stored-data requests require `X-NetAtlas-Read: 1`.
No CORS permission, cookies, credentials or browser authentication are supplied.
Vite proxies same-origin `/api` and `/healthz`; its listener remains loopback.

The header is a browser request guard, **not a secret or user authentication**.
Any trusted local program can read the synthetic data. Local users, OS/container
administrators and DB owners remain trusted. Do not forward/proxy this service to
remote clients or enable proxy-header rewriting; production accounts, least-privilege
DB roles, TLS, distributed rate limits and public access remain Phase 12 work.
There is no real-data authorization or field-level sensitive-content sanitizer.

## Routes and schemas

All stored-data routes use **POST with JSON** to keep filters and cursors out of
URLs/access logs and support bounded geographic objects. POST is read-only here.
Require `Content-Type: application/json`, no Content-Encoding, and an explicit
integer `schema_version: 1`. Unknown fields and duplicate keys fail. The same
`{"schema_version":1,"query":{...},"cursor":null}` envelope applies to all routes.

| Route | Request / response | Behavior |
| --- | --- | --- |
| `/api/v1/search` | SearchRequest / SearchResponse | Full Phase 6 query, exact counts/facets and bounded metadata hits. |
| `/api/v1/facets` | SearchRequest / SearchMetadata | Same post-filter counts/facets and provenance, no hits; cursor must be null. |
| `/api/v1/places` | PlacesRequest / PlacesResponse | Required exact dataset hash; optional exact casefolded name, country, kind; stable-ID ordering and continuation. |
| `/api/v1/endpoints/{address}/{transport}/{port}/detail` | EndpointRequest / SearchResponse | One current source for literal IPv4/IPv6, tcp/udp and port; unknown/deleted/expired/suppressed endpoint returns 404. |
| `/api/v1/endpoints/{address}/{transport}/{port}/history` | EndpointRequest / SearchResponse | Retained endpoint history, newest first; absent endpoint returns an empty page. |

EndpointQuery accepts selection (attempt/open/evidence), as_of, fresh_seconds,
exact pack/dataset hashes, engine/taxonomy identities and limit (history only).
Detail always uses one hit and rejects a cursor. Address is a literal with no DNS,
URL, CIDR or zone identifier; URI-encode IPv6 when composing paths. No source UUID
or evidence-blob download route exists. Detail is bounded search metadata, not raw
inspection or a merge of latest attempt/evidence/geo from different sources.

Example local read (no measurement):

```sh
curl --silent --show-error http://127.0.0.1:8000/api/v1/search \
  -H 'Content-Type: application/json' -H 'X-NetAtlas-Read: 1' \
  --data '{"schema_version":1,"query":{"selection":"evidence","limit":20}}'
```

The response contains canonical IP/port/transport, source UUID/hash/timestamps,
outcome, freshness/nonempty-evidence marker, selected derivation IDs, product/category
labels and candidate count, category ambiguity, network prefixes/multi-origin ASNs,
place ID/name/country/representative point and explicit accuracy radius/basis.
Pack/dataset metadata retains versions, hashes in selection, validity windows and
origin attribution/licenses/source hashes. Missing matches/radii remain null/unknown.
No candidate winner, verified identity, vulnerability, physical-device count or
precise location is inferred. Candidate confidence/evidence traces await Phase 9.

Only declared response fields cross the boundary. Source envelopes, scanner/contact
metadata, headers, cookies, bodies, certificate bytes, evidence offsets and private
paths are excluded. Place lists omit full boundary coordinates, but include kind,
admin code, origin, boundary interpretation and availability. The existing search
boundary filter accepts stable place IDs without transmitting polygons to clients.

All JSON escapes non-ASCII characters, controls and `<`, `>`, `&`; responses use
`application/json`, `nosniff`, `no-store`, and `no-referrer`. This is transport
escaping and field minimization, **not content anonymization or HTML sanitization**.
Decoded labels and URLs remain untrusted, including script-like strings and bidi
controls. Clients must render them as inert text, visibly handle controls where
needed, and never turn arbitrary metadata URLs into active links/resources.

## Semantics, places and clocks

[SEARCH.md](SEARCH.md) remains authoritative for selection-before-filtering,
current attempt/open/evidence, retained historical truth, exact identity choice,
product-label token AND search, geography, counts and post-filter facets. The API
reuses that SQL. All modes recheck source expiry and persistent suppression using
actual time after acquiring the shared lock, even with a historical as_of.

Selection.as_of reports the measurement cutoff; retention_checked_at reports the
actual clock; dataset_checked_at reports the geographic validity clock. A request
with explicit as_of describes historical enrichment at that time. Without explicit
as_of, dataset validity is rechecked at actual time on **every continuation page**,
even though the measurement cutoff/freshness reference stays pinned. Expired
geography cannot remain fresh merely because a cursor is still valid.

Counts distinguish unique endpoint keys, source observations and selected derivation
candidates. Multi-valued/history facets can exceed totals; total_buckets indicates
truncation. Facets include their own filter and cover the full matched set, never
just the page or remaining cursor suffix. Counts describe retained selected
observations, never worldwide prevalence, physical devices or complete coverage.

Places are a dataset-specific gazetteer, not observed endpoint counts. A known dataset
is exposed by this route only while at least one associated observation is unexpired
and unsuppressed. A missing/ineligible dataset returns the same 404. Stale/future
datasets return provenance/state with no places; current ones return bounded matching
places. Names are not identities: same-name rows keep distinct stable IDs/admin codes.
All rows in the retained dataset may be listed, including places with no matching
observed endpoint. No geocoding, nearest-place guessing or external lookup occurs.
Search pack/dataset provenance remains snapshot metadata for the exact requested hash,
including on empty hits; it does not assert a readable source or fresh dataset.

## Continuation and limits

Search/history use keyset order `(finished_at, started_at, UUID)` descending; places
use stable ASCII ID ascending. Continuation predicates apply **after** source choice
and content filters; exact totals/facets are unaffected. HMAC-SHA256 authenticated
cursors bind route/endpoint scope, canonical validated query, first-page cutoff,
resolved default pack hash, position and traversal budget. They contain no raw evidence or credentials.
Treat them as opaque: signed is not encrypted. Keep them private with the query.

Resubmit the **original query** with next_cursor. Do not copy the resolved selection
back as the request: its default pack hash/as_of have been expanded. Changing any
query value, endpoint or route invalidates the cursor. Tokens last 15 minutes from
the first page; subsequent pages do not renew the lifetime. A process restart creates
a fresh signing key and invalidates old tokens. Only one API process is supported.

This is a live retained-data view, **not a cross-request database snapshot**. New
sources/derivations, backfills, expiry and removals may change counts or matches.
Keysets prevent offset shifts/repeated source UUIDs within a forward traversal;
new rows above the cursor are not revisited. A current endpoint may acquire a
different selected source. Restart the query to refresh. Retention/suppression always
win; no cursor caches results or resurrects deleted data.

| Resource | Bound |
| --- | --- |
| JSON body / nesting / body read deadline | 16 KiB / 32 levels / 5 seconds, including streamed bodies |
| Text / place-name query | 256 characters |
| Search/history/place page | 1–200 items; default 50 |
| Facets | 1–50 buckets each; default 20; five kinds |
| HTTP offset | 0 only; use cursor |
| Cursor / lifetime / traversal | 2048 characters / 15 minutes / 10,000 search/history hits |
| Response JSON | 4 MiB, fail whole response rather than silently truncate |
| In-flight data requests | One per app process; immediate 429 while occupied |
| PostgreSQL statement / shared-lock wait | 5 seconds / 10 seconds |
| Gazetteer | Existing bundle cap 4096 places, exact filters over bounded rows |

At the traversal cap, next_cursor is null and page_limit_reached is true if additional
hits exist. Narrow the query to inspect further rows. Counts remain exact. Large
responses fail with 413; restart with smaller pages. One in-flight request is a local
cost guard, not requests-per-second policing or multi-process/global capacity.
Exact broad counts still scale with matched rows. Statement timeout can reject
expensive queries; no worldwide/concurrent performance claim is made.

## Stable errors and client contract

Errors contain only `{"error":{"code":"..."}}`, never validation input, SQL,
credentials, paths, labels or exception details. Relevant statuses:

| Status | Codes |
| --- | --- |
| 400 | invalid_cursor (tampered, wrong query/route, or restart) |
| 403 | forbidden (peer/Host/Origin/header policy) |
| 404 / 405 | not_found / method_not_allowed |
| 408 / 410 | request_timeout / cursor_expired |
| 413 | too_large / response_too_large |
| 415 / 422 | unsupported_media_type / invalid_request |
| 429 | busy (retry explicitly after the active request completes) |
| 503 / 500 | unavailable (including DB/lock/query timeouts) / internal_error |

OpenAPI is generated at `/openapi.json`; `/docs` provides interactive documentation.
`read_api/models.py` defines the allowlisted HTTP responses separately from private
search dictionaries. `web/src/api/schema.ts` is generated from the actual OpenAPI;
`web/src/api/client.ts` provides typed search/facets/places and endpoint calls,
AbortSignal support, same-origin paths, omitted credentials and redirect refusal.
Types are compile-time contracts, not a runtime response validator. Client failures
use known error codes and do not display arbitrary proxy error bodies.

```sh
uv run --locked python -m netatlas.read_api.contract         # regenerate types
uv run --locked python -m netatlas.read_api.contract --check # detect drift
```

The generator deliberately supports only the schema shapes in this reviewed contract
and fails on unknown shapes. Its OpenAPI digest detects bound/schema drift even when
TypeScript cannot express a constraint. `make check` includes drift, strict Python/TS,
web-client tests and builds. `make check-db` also covers real PostgreSQL route truth,
keyset ties/late inserts, cursor tampering/restart/expiry, unknown/ambiguous/stale data,
removal/read-time suppression/expiry, hostile metadata, cost bounds and SQL timeout.
All fixtures are synthetic; no Internet measurement or new datasets are used.

Phase 8 does not change these read contracts. Only package/health metadata changed;
the generated OpenAPI digest was updated. The UI shares one cancellable read lane,
uses original queries for continuation, and displays only one page with explicit
map scope. See [GEOGRAPHIC_UI.md](GEOGRAPHIC_UI.md).
