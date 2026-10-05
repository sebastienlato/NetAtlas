# Phase 13 — qualified synthetic findings

Measured **2026-10-05**, package **0.14.0**, workload `thesis-evaluation-1`, migration
**0006**. The [predefined protocol](EVALUATION.md) specifies units, denominators,
exclusions, clocks, sample selection, repetitions and uncertainty. All inputs are
authored; only four literal-loopback fixture services were contacted. This report
qualifies fixture behavior and local cost, not real-world accuracy or global capacity.

## Reproduction and provenance

The completed experiment used:

```sh
uv run --locked python -m netatlas.evaluation --at 2026-10-05T17:07:00Z --synthetic --measure --output data/thesis-evaluation-phase13.json
```

Choose a new ignored filename and a recent aware clock on later dates. The report
completed at **17:08:20 UTC** (13:08:20 America/Toronto). DB clock was explicitly
checked; authored times were no later than it. Source ages and bundle windows shift
with `--at`; identities derived from them consequently change. Repetition within
this run used exactly the same authored population/dataset hashes. Loopback ports,
UUIDs, clocks and manifest hashes legitimately vary and remain in private output.

The run was made on the Phase 13 working tree based on `ae511068830a81e77f84328211ff48c35f10d063`,
with dirty=true recorded honestly. The evaluated input-tree hash below covers sorted
path-to-SHA256 mappings of src Python/JSON, test-fixture JSON, pyproject and both locks;
documentation/Git commit metadata are excluded to avoid a circular report identity.
The delivery commit is identified by Git history and the completion report.

| Input | SHA-256 |
| --- | --- |
| Evaluated tree | `c3dc97e0b6cecb6599da41efc9cf405e18c7fca318588d8c03a7d2152d932082` |
| Canonical authored 30-case corpus | `4f77c7b3778b1142ea819c9ec5b11840b2a1425500b84d8863f518a655e17040` |
| Core assertion pack | `f01511ee63d87346e54d3171352f17a65807df5cb51933eee9cbd374d7d6a77b` |
| Performance-only core plus fictional rare-product pack | `2e57ab9cc97186fccd77c1ab79fb1e7e2b0dbe8f71bac14176c933ad5a07b12a` |
| Time-shifted authored enrichment bundle | `fe5b19808ea31d8c5d72c7fb849b63e78fea9f34d40cff1ffd45df50f6140ffd` |
| Ordered performance source digest population | `29673355ab4218338d4c293da130216270f931a38c5a4b889a17fa5a51a7a4f5` |
| Default Settings 3 | `5d5c77ec61c7b9ce81e6a54aae892a6ae90ed0b7f410cdc6257b816037b6b500` |
| Explicit loopback Settings 3 | `2e8b6b8ba5e5287a147f39e41831bc953e8faf8f889dab05d8dc39fecea91146` |
| Connection policy | `c334980eeb10e9bbd1b51c9b020da1926b8a7cd32b1ea2e031e1270c4f920e9f` |
| uv.lock | `d1489cb26b8f6b32ba48fefeb7ce46debd6cfc86b14e078831944d0741ee9abb` |
| web/package-lock.json | `9bc8e45108c4160f0a433b58d86ae542385d8a80a81d590552f37b96aaa97586` |
| Private completed JSON report | `35a291a50a2d50e8f760c3001e01ab08df1285955f2962bdc615a7973534c900` |

Fingerprint engine remains `fingerprints-1`, taxonomy `netatlas-categories-1`,
enrichment `enrichment-1`, scheduling `coverage-refresh-1`; production packs and
algorithms were not tuned. The performance pack is never used to score detection.
Original enrichment fixture, exact input files, schedule input/universe/policy/seed
hashes and per-case source/result hashes are recorded in the private JSON. These
are equality/provenance identifiers, not proof of independent authorship or accuracy.

Environment: Apple M4 Max, 64 GiB host RAM, 16 logical host CPUs, macOS 27.0.1 arm64;
Python 3.14.7, uv 0.12.19, Node 26.8.1, npm 11.19.0, cryptography 50.0.2. Existing
Colima netatlas VM: **2 CPUs / 2 GiB / 20 GiB**. Inspected DB container: **1 GiB /
2 CPUs / 256 PIDs / three 10-MiB logs**. PostgreSQL 18.3, PostGIS 3.6.4, 128-MB
shared_buffers, max_connections=100, fsync and synchronous_commit on. GEOS/PROJ
runtime versions reported 3.14.1/9.8.1; transitive image inputs remain imperfectly
pinned. No Python OS quota or database-volume quota. Test and benchmark clients use
two-connection pools, zero overflow and two-second waits. No concurrent regression
suite ran during timed trials. Existing app/body/SQL/lock/rate/reserve bounds remain.

## Detection, role inference and identity

Thirty purposely selected authored cases, not a random Internet sample. Labels were
written separately from predictions/rule IDs and kept fixed; one implementer authored
both scenarios and harness. No second-rater, blind or held-out validation is claimed.

Product-assertion scoring includes **29 labelled sources**; one incomplete header is
unlabelled and excluded, with no prediction emitted. There are **21 unknown-output
sources**, one multiple-product source and 11 candidate records across nine sources.
Deduplication for scoring gives 10 unique source-product pairs; duplicate rules are
not additional successful detections. Category scenarios label **25 sources**; five
negative/empty/ambiguous/opaque cases have no latent-role truth and remain excluded,
with zero predictions on those excluded cases. The same 21 sources have unknown
category output; one retains two role candidates.

| Captured product assertion | TP | FP | FN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| nginx | 6 | 0 | 1 | 6/6 = 100% | 6/7 = 85.7% |
| OpenSSH | 3 | 0 | 1 | 3/3 = 100% | 3/4 = 75.0% |
| Postfix | 1 | 0 | 0 | 1/1 = 100% | 1/1 = 100% |
| Apache (unsupported) | 0 | 0 | 1 | undefined, no predictions | 0/1 = 0% |

Perfect observed assertion precision has very small denominators. Nominal 95%
Wilson precision intervals are nginx **61.0–100%**, OpenSSH **43.9–100%**, Postfix
**20.7–100%**; recall intervals respectively **48.7–97.4%**, **30.1–95.4%** and
**20.7–100%**. Apache recall is **0–79.3%** nominally. These intervals demonstrate
small-sample sensitivity only; dependence and purposive selection prevent population
confidence claims. No global accuracy/F1 combines these different supports.

| Authored scenario category | TP | FP | FN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| web_server | 5 | 1 | 5 | 5/6 = 83.3% | 5/10 = 50% |
| ssh_server | 2 | 1 | 2 | 2/3 = 66.7% | 2/4 = 50% |
| mail_server | 1 | 0 | 1 | 1/1 = 100% | 1/2 = 50% |
| camera_nvr | 0 | 0 | 1 | undefined | 0/1 |
| router | 0 | 0 | 1 | undefined | 0/1 |
| nas | 0 | 0 | 1 | undefined | 0/1 |
| printer | 0 | 0 | 1 | undefined | 0/1 |
| vpn_appliance | 0 | 0 | 1 | undefined | 0/1 |
| database | 0 | 0 | 1 | undefined | 0/1 |
| iot | 0 | 0 | 3 | undefined | 0/3 |
| industrial | 0 | 0 | 1 | undefined | 0/1 |

The two spoof fixtures correctly expose asserted nginx/OpenSSH markers while their
authored IoT-emulator roles make the web/SSH category candidates false positives.
Latent software differs too. This is a constructive counterexample, not a measured
real spoof rate. Assertions, service roles and physical identity are separate claims.
NetAtlas supplies no device identity proof or physical-device precision/recall.

Failure and uncertainty ledger (case IDs are in the committed corpus):

- `case-variant`, `ssh-legacy`, `unrecognized-product`: uppercase nginx, legacy SSH
  and Apache assertions are missed. Literal matching/protocol/pack coverage explain
  these gaps; no rule change was made to improve the score.
- `hidden-nginx` and three decoys: correct absence of the evaluated product assertion
  yields no category, despite independently known web/SSH/mail roles. Product-marker
  recall and role recall therefore answer different questions.
- `incomplete-header`: unlabelled assertion, unknown output, known web-role miss.
  `complete-header-short-body`: complete header still supports a candidate; incomplete
  body is not silently recast as complete evidence.
- Eight unsupported-class cases all abstain. Their role false negatives remain in
  the table. The extra two spoofed IoT scenarios make IoT support three, not one.
- `bare-220`, `unknown-bytes`, `empty-open`, `timeout`, `closed`: explicit unknowns;
  no latent role is invented. Refusal and timeout are not negative product identity.
- `two-products` preserves nginx/OpenSSH and both categories. `duplicate-marker`
  produces two records but one product/role pair. Neither implies two devices.

## Exact retrieval, freshness and geography

Ten source-ID/count oracles, explicit category/ASN/country/geography facet oracles,
source-bound inspection and stale/future-dataset checks all passed. Seven authored
sources describe six endpoints; history preserves an old positive plus a new timeout.

| View | Endpoints | Sources | Candidate records |
| --- | ---: | ---: | ---: |
| Latest attempt | 6 | 6 | 4 |
| Latest nonempty evidence | 5 | 5 | 5 |
| Retained attempt history | 6 | 7 | 5 |
| Current nginx filter | 2 | 2 | 3 |
| Stale nonempty evidence | 1 | 1 | 1 |
| Unknown point/mapping | 2 | 2 | 0 |
| IPv6 current attempts | 2 | 2 | 3 |

Attempt ages at the fixed cutoff are **10,20,20,20,20,20 seconds**; evidence ages
are **20,20,20,20,200000 seconds**. The latest timeout is fresh as a measurement,
while its preserved positive evidence is about 55.6 hours old. A current product
filter does not fall back to that old evidence. Freshness is age under a 24-hour
policy, not uptime, detection probability or evidence that a real service changed.
Expired/future selected bundles each leave all six current sources visibly stale/
not-yet-valid with no usable network/place fields. Wrong endpoint/source binding
returns generic 404; valid two-candidate inspection checks exact traces.

Four of six current sources have points; two remain unmapped (one known place with
no coordinate, one missing mapping). **2/4 IPv4** and **2/2 IPv6** sources have points.
Three of the four mapped points lack a provider radius; the remaining authored
radius is 250 km, not an error measurement. Country associations are FJ=3, US=2,
unknown=1, including the known country without a point. Same-name east/west places
retain separate IDs. These tiny fictional associations demonstrate missingness bias:
map-only counts omit a third of selected sources and differently omit IPv4/IPv6.
They establish no country prevalence or geolocation accuracy. The basemap remains
Fiji-only and displayed clusters remain page-scoped.

The routing fixture contains **12 routed, 2 unrouted and 4 unknown IPv4 addresses**.
IPv6 has two routed regions, one unknown region, two routed seeds, one nonrouted
seed and one routed region with no seed. One port yields **14 candidates**, not an
IPv6-space denominator. Baseline schedules 14; an exclusion/blocked trial partitions
14 as 2 excluded + 1 blocked + 11 scheduled. Bounded sampling at seeds 7/8/9 partitions
14 eligible into **6 sampled out + 1 queue deferred + 7 scheduled** each time.
The first six dispatches give each populated /24-/48 two positions. Shard populations
are **3/1/3**, **1/4/2**, **2/3/2**; partitions are neither equal work nor new budgets.
All three seeds select both routed IPv6 seeds but only 5/12 routed IPv4 addresses.
Selection membership changes; seedless IPv6 remains entirely unseen. No measurement
or completion claim follows from an offline schedule.

At one second before the two-day timeout cooldown, the latest negative source is
fresh; at equality it becomes one refresh referencing that exact latest source UUID/
digest, not the older open source. This verifies policy, not an empirically optimal
refresh interval. Actual admitted/measured/incomplete/retained/refreshed distributed
counts remain distinct and are regression-tested separately, not fabricated here.

## Complete operation latency and throughput

Three fresh DB repetitions, 384 sources each, ten timed serialized complete queries
per shape after one excluded warm-up; one client, warm caches, 50-row maximum page,
full exact counts/facets included. p50 is the median; p95 is nearest rank and therefore
the maximum of ten samples per repetition. Milliseconds below show **run 1 / 2 / 3**.

| Query | Endpoints / sources | p50 ms | p95 ms |
| --- | ---: | --- | --- |
| all_current evidence | 128 / 128 | 8.317 / 7.967 / 7.878 | 10.244 / 8.671 / 9.171 |
| all_history evidence | 128 / 352 | 14.305 / 14.163 / 14.258 | 15.301 / 15.172 / 14.704 |
| network | 16 / 16 | 4.624 / 4.453 / 4.525 | 5.139 / 5.159 / 4.935 |
| port | 128 / 128 | 8.628 / 8.523 / 8.607 | 9.400 / 8.968 / 9.055 |
| text_rare | 2 / 2 | 3.611 / 3.710 / 3.603 | 3.834 / 4.161 / 3.929 |
| category | 128 / 128 | 8.690 / 8.731 / 8.523 | 9.744 / 9.757 / 9.657 |
| asn | 64 / 64 | 8.371 / 8.463 / 8.337 | 9.177 / 14.105 / 8.628 |
| radius | 64 / 64 | 8.186 / 8.486 / 7.957 | 8.730 / 9.136 / 8.262 |
| dateline_box | 128 / 128 | 11.231 / 11.441 / 11.184 | 12.945 / 12.639 / 13.267 |
| fresh evidence | 96 / 96 | 7.318 / 7.619 / 7.192 | 7.639 / 7.798 / 7.750 |

Candidate counts equal source counts in this performance-only population; the
functional corpus separately tests ambiguity. Every timed result was checked against
independent expected counts/page source IDs. No failures or unplanned backpressure
occurred. Run 2 ASN tail variation remains visible; 30 samples across three runs
are insufficient for a production tail SLA. No HTTP transport/browser rendering,
concurrent readers/writers, cold cache, remote RTT or sustained saturation is measured.

Timed write work performs ingest + fingerprint + enrichment for every new source
(**three commits per source**), including fixture construction/serialization. Across
the 96 then 288 new sources, total times were **3.537 / 3.415 / 3.440 seconds**,
or **108.6 / 112.5 / 111.6 completed sources/s**. This is fixture pipeline throughput,
not collector rate, an atomic three-stage transaction or worldwide ingest capacity.
Migrations, vacuum, read warm-ups and verification are excluded; dataset/rule
snapshot setup performed by those actual writes remains included.

Four standalone loopback services, two slots, global 10/s and per-prefix 1/s:

| Measured run | Capture + fsynced spool s | Ingest + derive s | Search s | Total s | Sources/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 3.0134 | 0.0635 | 0.0042 | 3.0812 | 1.2982 |
| 2 | 3.0086 | 0.0501 | 0.0041 | 3.0628 | 1.3060 |
| 3 | 3.0100 | 0.0620 | 0.0043 | 3.0762 | 1.3003 |

Each has four attempted/completed sources, zero incomplete, exactly four connections,
three product candidates and one unknown. The one excluded warm-up took 3.0802 s.
Four starts span about three spacing intervals, so the finite-campaign 4/elapsed
ratio can exceed 1/s without violating one start per prefix per second. It is not a
sustained traffic rate. Services send authored greetings; this does not benchmark
TLS, slow/large peers or distributed central-permit overhead. Existing real two-worker
HTTP/TLS failure acceptance supplies safety evidence, not timing extrapolation.

## Storage growth and failure behavior

All three repetitions observed the same allocated footprint after VACUUM ANALYZE:

| Stored endpoints / sources | App relations incl. indexes B | Index subset B | Logical blobs B / files |
| --- | ---: | ---: | ---: |
| 0 / 0 | 565,248 | 401,408 | 0 / 0 |
| 32 / 96 | 1,974,272 | 901,120 | 94 / 2 |
| 128 / 384 | 4,276,224 | 1,810,432 | 94 / 2 |

Growth was **1,409,024 B** for the first 96 sources and **2,301,952 B** for the next
288. The 384-source increase above empty schema is **3,710,976 B**. Do not add the
index column to the relation column: indexes are already included. Only two short
payloads are repeated, so 94 deduplicated blob bytes are deliberately unrepresentative
of real captures. Equal content never collapses the 384 distinct measurement rows.
Sources each have one fingerprint and enrichment result; all 384/384/384 replayed.

These are allocated app tables/TOAST/index bytes and logical blob lengths, excluding
PostGIS reference tables, WAL, backups, VM disk, logs, physical filesystem blocks,
future removals and operational copies. Small checkpoint slopes are not a linear
capacity forecast; page allocation, metadata and repetitive evidence dominate.

One deliberately injected blob-reserve denial in a separate empty DB rejected the
write with **zero acknowledged sources, source rows, outbox rows or evidence refs**.
Removing the injection allowed insertion; exact replay returned replayed. No owner
disk was filled, DB interrupted or resource bound relaxed. This is error-path evidence,
not an exhaustion/recovery-time benchmark. Full regression additionally checks bounded
HTTP contention, worker pending preservation, stop/opt-out, lost acknowledgements,
uncertainty/fencing and stopped restores under their existing contracts.

## Interpretation and remaining validity limits

OpenSearch remains deferred. These small warm local results reveal no reason to add
an asynchronous private-data copy; they do not prove PostgreSQL meets larger/concurrent
workloads. The [Phase 6 benchmark](SEARCH_BENCHMARK.md) is a labelled historical
2,048-endpoint, single-client result under earlier resource settings, not a comparable
before/after speedup. No bandwidth, energy or worldwide operating-cost trial ran.

Purposive easy markers, very small support, same-author labels, fixed ports, skewed
geography, short duplicate payloads and one local vantage limit external validity.
Real nonresponse, NAT, shared IPs, anycast, churn, load balancers, named virtual hosts,
IPv6 seed provenance, protocol gaps, source retention and dataset age all change
coverage. Unknown geography is not randomly missing. Exposure is not vulnerability.
A separately authorized institutional inventory study is proposed in EVALUATION.md;
it is not needed to complete this synthetic phase and has not been executed.

The generated detailed report remains ignored/private, with normal disposable DB/blob/
spool cleanup. Owner source/derivation/enrichment counts were 2/1/1 before evaluation;
final verification and full regression results are recorded in PROJECT_STATE. No owner
credentials, service grants, worker boot state or volume were reset. Phase 14, releases,
tags, public deployment and real-world campaigns remain outside this delivery.
