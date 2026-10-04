# Phase 6 synthetic search benchmark

Measured 2026-10-04, workload `synthetic-search-1`, package 0.7.0 / migration 0004.
All observations, IP/ASN associations and labels are authored fixtures. No target
measurement, Internet lookup, commercial discovery dataset or raw-capture export.
This is a single-client local demonstration, not a worldwide capacity evaluation.

## Reproduce

From the repository root with the existing private Compose database running:

```sh
make db-up COMPOSE=docker-compose
uv run --locked python -m netatlas.search.benchmark --endpoints 2048 --samples 20 --at 2026-10-04T22:00:00Z --output data/search-benchmark.json
```

Use a new output filename and a recent aware UTC `--at` on later dates. It must be
within the last 20 days so the two-day history remains within source retention.
Source/dataset times shift with that explicit clock; count expectations stay fixed.
The script creates a uniquely named disposable `netatlas_test_bench_*` database,
applies packaged migrations and ingests through the real synthetic pipeline with
temporary private blobs. It drops only that database and cleans temporary blobs in
finally; it does not edit the operator database, volume or credentials. Full query
plans and results are private mode-0600 ignored output. Interrupted process/host loss
may require cleanup of its explicitly identified disposable database.

Endpoint count is bounded to 1–4096 and samples to 1–50. Seed identities, endpoint
mapping and observation ordering are deterministic. UUID values are authored; real
measurements are never substituted. `VACUUM ANALYZE` precedes measurement. One warm-up
per query is excluded; 20 complete Python service calls then measure wall-clock time
(including DB transaction/lock, SQL, exact aggregates/facets, 50-hit page and JSON
transfer). p50 is the median, p95 the nearest-rank 95th percentile. EXPLAIN ANALYZE
BUFFERS plans are collected separately and excluded from timed samples. The full
query code uses ordinary PostgreSQL planner settings; no forced index plans.

## Workload and environment

- 2,048 endpoints: half literal TEST-NET-1 IPv4, half 2001:db8::/32 IPv6. Four ports
  8000–8003 distinguish repeated IPv4 addresses. Three observation attempts each,
  at two days/one day/current second before the chosen clock: **6,144 sources**.
- Every fourth endpoint's latest attempt times out; prior evidence survives. All
  other attempts carry authored HTTP server literals. Every hundredth endpoint has
  the fictional `NetAtlasBenchRare` product; others match the core nginx assertion.
  Each source has one chosen fingerprint and enrichment result: 6,144 of each.
- Default benchmark selection is **evidence**, giving 2,048 current sources or 5,632
  nonempty historical sources. There are 21 rare-product endpoints, 64 selected
  network endpoints, 512 selected ASN/radius/port endpoints and 1,536 fresh sources.
  Counts are asserted; repeated result pages and facets must match exactly.
- The existing authored enrichment fixture supplies two dateline representative
  points, independent IPv4/IPv6 prefixes, multi-origin ASNs and same-name place IDs.
  This intentionally narrow geography is not a global distribution or realistic
  selectivity model. Additional correctness tests cover gaps, expired/future bundles,
  uncertain radii, holes, invalid input and removed sources.
- Apple M4 Max, 64 GiB host RAM, macOS 27.0.1 arm64. Dedicated Colima/VZ Linux VM:
  **2 CPUs, 2 GiB RAM, 20 GiB disk**. PostgreSQL 18.3 / PostGIS 3.6.4 native arm64,
  standard local Compose settings. Python 3.14.7, uv 0.12.19, SQLAlchemy/psycopg locked.
  Timed queries ran without concurrent test/measurement workload. Warm filesystem/DB
  caches; no cold-cache, remote-network, concurrent-client or hardware-failure trial.
- Final seed time: **57.133 seconds** through durable per-row transactions, including
  derivation/enrichment. This is setup time, not scanner or production ingest throughput.

## Final measured latency

Milliseconds, complete exact-query service calls; query names match the script.

| Query | Endpoints | Observations | p50 ms | p95 ms |
| --- | ---: | ---: | ---: | ---: |
| all_current | 2,048 | 2,048 | 80.654 | 110.748 |
| all_history | 2,048 | 5,632 | 189.576 | 218.576 |
| network | 64 | 64 | 6.656 | 7.378 |
| port | 512 | 512 | 23.495 | 27.476 |
| text_rare | 21 | 21 | 4.085 | 4.915 |
| category | 2,048 | 2,048 | 95.278 | 115.968 |
| asn | 512 | 512 | 38.559 | 39.927 |
| radius | 512 | 512 | 37.481 | 39.580 |
| dateline_box | 2,048 | 2,048 | 152.394 | 156.081 |
| fresh | 1,536 | 1,536 | 61.194 | 62.608 |

`network` is 192.0.2.0/28; `port` is 8000; `text_rare` is NetAtlasBenchRare;
`category` is web_server; `asn` is 64497; `radius` is 1000 metres around
(179.5, -17.5); `dateline_box` is west=170/south=-20/east=-170/north=-10;
`fresh` uses the 86400-second threshold. All include chosen dataset/pack metadata,
exact counts and all five facet types. All-history means evidence history here;
attempt history would include all 6,144 rows.

Unforced plans used `search_address` for the selective CIDR, `search_product_text`
for rare text, `search_enrichment_fields` for ASN, `search_enrichment_point` for radius,
and `search_enrichment_geometry` for the dateline box. Source PK/endpoint ordering
and result-choice indexes also participated. Broad current/history/category/port/
fresh queries favored scans with the enrichment-choice index. This is expected;
forcing indexes is not a performance goal. Acceptance separately proves expression
compatibility of the B-tree/GIN/GiST predicates on small fixtures with seqscan off.

## Index footprint and choice

Post-vacuum `pg_relation_size` for the nine added indexes (allocated bytes, not just
live keys; values vary with page packing, GIN pending-list flushes and maintenance):

| Index | Bytes |
| --- | ---: |
| search_address | 204,800 |
| search_enrichment_choice | 1,343,488 |
| search_enrichment_fields | 2,998,272 |
| search_enrichment_geometry | 327,680 |
| search_enrichment_point | 524,288 |
| search_fingerprint | 1,769,472 |
| search_port_time | 516,096 |
| search_product_text | 81,920 |
| search_time | 548,864 |

Added indexes total **8,314,880 bytes (7.93 MiB)**. All user indexes, including prior
PK/FK/retention/outbox indexes, total **15,622,144 bytes (14.90 MiB)**. These are index
sizes only, excluding heap/TOAST, raw blobs, WAL, dumps and VM overhead. JSONB indexes
also index immutable provenance fields; targeted smaller projections can be evaluated
later if that cost becomes material. No claim of bit-identical physical size across
runs, architectures or PostgreSQL maintenance timing.

Nine indexes have specific query roles. inet GiST supports containment; port/time
and finish/start/UUID support selective structured/time ordering; JSONB GIN supports
candidate/ASN/place predicates; tsvector GIN limits text to product labels; enrichment
choice supports exact result identity/evaluation selection; geography GiST supports
metre radius; geometry-expression GiST supports split planar box/boundary predicates.
They avoid extra source copies and remain transactionally consistent with deletion.

**Decision: do not add OpenSearch.** Selective queries are about 4–39 ms median and
the broad evidence-history query about 190 ms on this small constrained VM. These
results do not demonstrate a bottleneck that justifies a second service, duplicate
private metadata, asynchronous deletion coordination and another rebuild/backup
system. They also do not prove PostgreSQL will meet worldwide scale. Reconsider
with larger retained histories, skewed/high-cardinality facets, concurrent read/write
clients, cold caches or required text semantics; compare correctness, p95 cost,
index/WAL growth and operational/removal guarantees before changing the architecture.
