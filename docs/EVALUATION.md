# Phase 13 — synthetic thesis evaluation protocol

Workload `thesis-evaluation-1`. This protocol is fixed before the first reported run.
The companion [report](EVALUATION_REPORT.md) records actual results and limitations.
No real-world accuracy, physical-device identity or worldwide capacity is qualified.

## Questions and authored truth

The new 30-case `src/netatlas/evaluation/corpus.json` is a purposive census of authored
scenarios, separately labelled before running the engine. It does not copy rule IDs,
expected engine outputs or predictions into truth. Every case has a rationale, raw
inert synthetic text, captured product-assertion labels, scenario role labels and
optional latent software labels. Production rules are held fixed. This is independence
from predictions, not independent authorship by a second researcher, blinding, a
held-out statistical sample or external validation. Existing 47-case Phase 3 tests
remain regression evidence, not the new evaluation denominator.

Product assertion means a product identified in an authored identity-bearing field,
including unsupported products, legacy syntax and case variants. Quoted body text,
SSH comments and hostnames are decoys. An incomplete field is unlabelled (`null`),
not a negative; a complete field on a partial body remains labelled. `[]` means
labelled absence of a product assertion in the evaluated evidence. Scenario roles
are authored service/device-class facts, not labels generated from matching rules.
A marker can be detected correctly while its role inference is wrong. Multiple
roles are retained; no arbitrary winning candidate is scored. Latent software is
used only as a counterexample to interpreting assertions as actual software identity.
There is no physical-device identity evaluator or labelled real-device population.

For each product and each of all 11 positive taxonomy classes, the scoring unit is
one **unique source-label pair**. TP/FP/FN are set intersection/differences on labelled
cases. Precision is TP/(TP+FP); recall is TP/(TP+FN). Zero denominators are null,
not 0 or 100%. Unlabelled sources, predictions on those sources, sources with no
outputs, multiple outputs and total candidate records are separately reported.
Unsupported classes remain in recall denominators. No aggregate accuracy, weighted
F1 or true-negative score hides missing classes. Per-case failures and per-stratum
unknowns are retained. Nominal Wilson 95% intervals describe small denominator
sensitivity only: authored dependent cases do not support population confidence.
No performance threshold tunes or deletes inconvenient corpus rows.

## Functional and bias experiments

A separate small authored source history supplies exact expected source IDs/counts
for attempt/evidence/history, current negative outcomes, stale evidence, geography
gaps, IPv4/IPv6 and same-name places. Expectations are explicit fixture facts and
are checked against SQL output, not a warm-up prediction. Exact source-bound
inspection rechecks evidence linkage. Expired/future datasets and wrong source IDs
must not fabricate usable geography/evidence. Retention/suppression/backpressure
acceptance continues in the full suite.

Offline authored routing experiments report routed/unrouted/unknown IPv4 address
counts separately from IPv6 regions and explicit seeds, exclusions, blocked/fresh,
eligible, sampled-out, deferred and scheduled. Fixed seeds 7/8/9 expose selection
variation; logical shards do not expand budgets. Outcome cooldown boundary checks
include latest negative history and never turn delivery replay into refresh.
Fairness is dispatch order only. No IPv6 address-space coverage fraction is computed.

## Performance, clocks and resource budget

Default and maximum experiment: three fresh disposable DB repetitions, 10 measured
samples per search shape per repetition and one excluded warm-up per shape. For a
quick check, one repetition/two samples is permitted and is not the thesis timing
run. No parallel load generator; one client, the existing shared transaction lock,
two DB connections, zero overflow and two-second connection/pool waits remain.

The fixed Phase 6 authored workload is reused at growth checkpoints **32 and 128
endpoints**, with three attempts each (96 then 384 immutable sources). Every fourth
latest attempt is negative. The second checkpoint only adds new endpoints. Each
source's ingest, fingerprint derivation and enrichment commits are included in timed
write work; this is a three-transaction durable source pipeline, not atomic combined
publication or scanner throughput. Migration, fixture construction, verification,
VACUUM ANALYZE and query warm-ups are outside read timings. Write timings include
fixture construction and per-row serialization, explicitly part of the operator
seed operation. Report seconds, sources/second and commit counts, never devices/s.

Ten Phase 6 query shapes measure complete Python search calls, shared lock, exact
aggregates/facets, bounded 50-row page and JSON serialization. Expected counts and
page identities come from independently specified workload algebra for the fixed
128 endpoints, not earlier query output. Timing excludes oracle comparison.
Each sample is retained privately. Median and nearest-rank p95 are per run; min/max
and cross-run ranges expose dispersion. Ten samples make p95 the maximum; do not
claim a stable tail SLA. Caches are warm, no cache eviction or cold-start claim.
Historical Phase 6 2,048-endpoint numbers retain their original scope/environment.

A separate literal-loopback fixture uses four authored greeting endpoints and two
standalone discovery slots at the existing default rates (10 global, 1/prefix per
second). One warm-up plus three measured campaigns include bounded capture, final
fsynced spool, durable ingest/derive and a complete retained search. Report each
stage, complete sources/elapsed second, attempted/completed/incomplete counts and
actual connections. This is **standalone local pipeline throughput**, not distributed
worker throughput. The existing two-process authenticated HTTP/TLS/lost-ACK/fencing
acceptance remains separate safety evidence. No new worker network or owner
coordinator is provisioned. Fixture setup/listen is excluded; fixtures always close.

Use `perf_counter` for durations; explicit aware UTC `--at` for authored sources,
dataset validity, query cutoff and offline schedules. The clock must be recent
(within 20 days) for ordinary actual-time 30-day retention. The runner additionally
checks DB time; it never resets clocks or retention. Loopback observations use the
collector's actual UTC clock and random measurement IDs/ports; those values are
recorded privately through manifest/source hashes, not promised byte-reproducible.
No random sampling outside the explicitly recorded schedule seeds is introduced.

Storage records empty/post-96/post-384 allocated application relation bytes (heap,
TOAST and indexes, excluding PostGIS spatial_ref_sys), index bytes separately,
logical private blob bytes/files and exact source counts. Deltas are observed page
allocation, not a universal per-source slope. Duplicate bytes share blobs; negative
attempts remain separate rows. WAL, VM disk, backups, deleted free pages, logs and
filesystem allocation overhead are excluded; no disk-fill trial. Injected reserve
failure in an isolated DB must produce no source acknowledgement, row or outbox,
then succeed once the injected failure is removed. It measures fault behavior, not
physical resource exhaustion or recovery-time assurance.

Provenance includes code revision/dirty flag and evaluated source-tree content hash,
package/Python/platform/CPU count, dependency lock hashes, core and benchmark pack,
dataset, source population, configuration, policy, corpus, input/universe/seed hashes,
UTC and monotonic clock definitions, PostgreSQL/PostGIS and queried DB settings.
Container/VM limits must be inspected and recorded in the report, not inferred from
host CPU count. There is no OS quota on the Python process and no DB volume quota.
Configured SQL timeouts, transport bounds and 64-MiB reserve are never relaxed.
Any trial failure aborts publication with a generic diagnostic; incomplete runs
must not be reported as successful samples. Failure/backpressure reports are separate
from successful-operation latency. No paid infrastructure or external targets.

## Reproduce and keep private

From the repository root, after reviewing the existing runtime:

```sh
make db-up COMPOSE=docker-compose
make db-migrate
uv run --locked python -m netatlas.evaluation --at RECENT_AWARE_UTC --synthetic --measure --output data/thesis-evaluation-NEW.json
make check-db COMPOSE=docker-compose
```

Use a new filename; private publication is atomic/no-clobber. Measured sources,
spools, DBs and blobs are temporary, final machine-readable output is mode 0600 under
ignored data/. Never commit it. The committed report is an authored aggregate
analysis with provenance, not a source/capture export. Normal completion/failure
cleans only newly created `netatlas_test_eval_*` DBs and temporary directories.
Abrupt termination may require manual cleanup of those identifiable disposable DBs;
owner data, credentials, volume, worker boot files and service grants stay untouched.

## Separately proposed external validation

A future study could use a consented institution-owned inventory, independently
recorded service/product/role ground truth and multiple approved vantage points.
Before any such work, the owner and institution must resolve written scope and
network permission, ethics/privacy requirements, operator contact/opt-out response,
minimal data handling/access/retention, lawful dataset rights and a stop procedure.
Design stratified IPv4/IPv6/protocol/location samples, blind labels to predictions,
record nonresponse and unavailable truth, and pre-register scoring/budgets. Inventory
identity must be separately verified; banners, IPs, NAT, anycast and geolocation are
not device identity. This is a proposal only, with no approval assumed and no traffic,
real ingestion, deployment or automatic follow-up authorized by Phase 13.
