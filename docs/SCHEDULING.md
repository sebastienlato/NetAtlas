# Phase 11 — synthetic coverage and refresh scheduling

Package **0.12.0**, schedule input/plan schema **1**, algorithm **coverage-refresh-1**,
IPv6 policy **explicit-authored-seeds-only-1**, migration **0006**. Control envelope 1,
Settings 3, source/manifest 2, explicit v1 reads and HTTP/local query schema 1 remain
unchanged. This is a bounded authored routing simulation and local execution adapter.
No routing downloads, real input, Internet campaign, global completeness, physical
device count, prevalence estimate or public deployment is implemented or authorized.

## Boundaries and provenance

`scheduler/models.py` and `planner.py` are I/O-free. A `PlanningInput` carries an
explicit aware clock, versioned universe, schedule policy, non-secret Settings,
optional source summaries, blocked endpoints and suppression CIDRs. The universe
names its ID/version, inclusive validity start/exclusive expiry, origins, disjoint
regions, IPv6 seeds and ports. Origins record ID/version, claimed content checksum,
attribution/license and `authored-synthetic`. Hashes identify inputs; they do not
verify authorship, permission or the truth of a routing assertion. There is no URL
fetcher, live BGP input or automatic source renewal.

Regions explicitly assert `routed`, `unrouted` or `unknown` **within the fixture**.
Only TEST-NET-1/2/3, 2001:db8::/32 and the two literal loopback host networks are
accepted. Overlapping regions, including equal prefixes, fail; there is no implicit
longest-prefix routing override. Addresses outside declared regions are outside this
universe and remain unknown, not globally unrouted. IPv4 expansion includes first
and last addresses. Arithmetic bounds are checked before any enumeration.

IPv6 never enumerates a network, infers low addresses, generates EUI-64 addresses,
resolves names or expands a discovered neighbor. Only explicit unique literal seeds
inside a declared region are candidates. Each seed has a referenced origin; the
universe validity window applies to its seed set. Seeds in unknown/unrouted regions
are counted but not scheduled. A routed IPv6 region without seeds is visibly seedless.
Seed bias is unknown and not random coverage of its /48 or /32 address space.

The plan retains separate canonical SHA-256 identities for input, universe, schedule
policy, ordered seed documents, Settings and the inherited connection policy. Ordered
arrays are part of canonical identity. A plan identity is SHA-256 of the canonical
plan; each scheduled entry hashes input identity plus canonical endpoint key. Input
clock, history, exclusions or policy changes therefore produce a new schedule identity.
Original source UUID/hash/start/finish/outcome remain separate. Canonical serialization
uses validated defaults, sorted keys and compact ASCII JSON, as for existing sources.

## Selection, sampling, shards and fairness

1. Build candidates from routed IPv4 addresses and routed IPv6 seeds × explicit TCP
   ports. Operator exclusions, opt-outs, supplied suppression snapshots and narrowing
   allowlists apply before freshness; a blocked endpoint is never selected.
2. From supplied history select the latest retained attempt by finish/start/UUID,
   including negative/empty sources. Sources at or beyond 30 days are excluded from
   this selection. Future history fails. No older-open/evidence fallback is used.
3. A retained source is due at finish + the configured outcome interval: defaults
   **open 1 day, refused 7 days, timeout/error 2 days** (each configurable 60 seconds
   to 30 days). Equality is due. Missing retained history is coverage, not a refresh.
   These authored priorities are a policy choice, not learned change rates or uptime.
4. Group by fixed /24 IPv4 and /48 IPv6. Within each prefix, oldest due time wins;
   SHA-256 ranking of algorithm/seed/endpoint breaks ties, with endpoint as final
   tiebreak. Previously unseen entries are due at the planning clock. Select at most
   `sample_per_prefix` (1–128), reporting the remaining eligible entries as sampled out.
5. SHA-ranked prefixes are traversed round-robin, one entry per nonempty prefix per
   round, to the global queue bound. `policy.round` rotates the starting prefix. With
   an unchanged eligible prefix set, N consecutive explicit round values visit every
   prefix even with a one-entry queue. Repeating the same input repeats the same plan.
   Changing eligible sets or failing to advance round gives no cross-plan starvation
   guarantee. Entries left over are counted as queue deferred; no hidden spill queue.
6. Each selected entry gets `SHA256(algorithm/seed/"shard:"/endpoint) mod shards`,
   for 1–32 logical shards. Labels partition the one globally bounded plan exactly;
   small shards can be empty and loads need not balance. These are reproducible
   partitions, not extra worker identities, campaigns or independent traffic budgets.
   The lab adapter admits the combined ordered plan; workers claim from one queue.

This is fairness of **scheduled dispatch order**, not equal socket time, successful
responses or completion latency. Prefix pacing, slow collectors, occupied uncertain
slots, cancellation, expiry and storage failure can reduce measured coverage. A
lease reassignment preserves its queue position; only pre-permit leases can reassign,
with the inherited maximum of three assignments. Busy prefixes still have to use the
central budget. Neither a shard nor a refresh introduces a second rate limiter.

## Denominators and reported states

`plan.counts` distinguishes routed/unrouted/unknown IPv4 **addresses**; IPv6 **regions**,
routed/nonrouted seeds and seedless routed regions. It deliberately has no total IPv6
address coverage percentage. Endpoint candidates use only routed IPv4 + routed seeds
multiplied by ports. Planning partitions satisfy:

```text
candidate_endpoints = excluded + blocked + fresh + eligible
eligible = sampled_out + queue_deferred + scheduled
scheduled = coverage + refresh
```

Counts are for the declared fixture, selected ports, clock and exact policy. They do
not describe devices, worldwide coverage, exposed population or retained evidence.
`expired_history` counts ignored supplied source summaries, not endpoint exclusions.
Changing exclusions changes the denominator; compare plans with their full identities.
No configured exclusions are silently counted as measurement failure.

`report --campaign UUID` separately reads durable execution truth:

| Count | Meaning |
| --- | --- |
| scheduled | Jobs committed for this schedule, including stopped/expired work. |
| admitted | Jobs with at least one central permit; a lost/slow grant may never dial. |
| permits_issued | All grants, including TLS/second connections and burned grants. |
| measured | Complete original observations with committed delivery receipts, including negative/empty outcomes. Worker-local saved but undelivered results are not counted. |
| queued / active | Waiting jobs / leased or measuring jobs after lease reconciliation. |
| not_admitted | Terminal cancelled/failed jobs with no issued permit. |
| incomplete_or_uncertain | Terminal issued jobs lacking a committed result. Does not invent an observation or prove failure to connect. |
| retained | Receipt-bound source rows still unexpired and unsuppressed at the actual report clock, even before physical cleanup. |
| refreshed | Committed measured jobs explicitly linked to a previous source UUID/hash; independent of whether either source is still retained. |

Counts overlap intentionally: measured, retained and refreshed are different stages,
not a sum. Cancellation/removal does not erase receipt history. Report checks the
saved schedule hash by recomputing from its immutable input snapshot, and shows its
campaign deadline/expiry, cancellation and current global stop state. It exports
counts/identities only. Source summaries and schedule documents remain private control
metadata with the inherited 90-day prune policy, not additional 30-day raw evidence.

## Operator workflow

Prepare an authored `PlanningInput` JSON under ignored `data/`, using the model schema
and a current validity window. It needs `schema_version:1`, `at` and `universe`;
policy and Settings default to safe disabled measurement. To inspect the complete
local schema without any data or network operation:

```sh
uv run --locked python -c 'import json; from netatlas.scheduler.models import PlanningInput; print(json.dumps(PlanningInput.model_json_schema(), indent=2))'
uv run --locked netatlas-schedule plan --input data/schedule-input.json --output data/schedule-plan.json
uv run --locked netatlas-schedule enqueue --input data/schedule-input.json
```

Both commands above are offline. The second is a **preview** by default, creates no
DB connection and authorizes no traffic. Plan files are private no-clobber outputs;
console output contains hashes/counts only. The plan file is an audit output, not an
execution token. Enqueue consumes and recomputes the original input, never trusts a
caller-edited list of selected entries. Files are regular, bounded, non-symlink JSON;
duplicate keys, depth over 32, unknown fields and missing outer schema version fail.

For a separately authored loopback fixture plan, set `lab_loopback:true`, use only
`127.0.0.1/32` and/or `::1/128` regions (with explicit `::1` seed), and provide enabled
operator Settings. At most 16 ports / 32 endpoint jobs are executable. The adapter
rejects other universe regions; it never maps documentation addresses onto loopback.
An explicit snapshot obtains current DB-clock history/suppressions/unresolved attempts:

```sh
make db-up COMPOSE=docker-compose
make db-migrate
uv run --locked netatlas-schedule snapshot --input data/lab-template.json --output data/lab-current.json
uv run --locked netatlas-schedule plan --input data/lab-current.json --output data/lab-plan.json
uv run --locked netatlas-schedule enqueue --input data/lab-current.json --synthetic --measure
uv run --locked netatlas-schedule report --campaign CAMPAIGN_UUID
```

Use new filenames on repeat. `snapshot` replaces input history, blocked endpoints,
suppressions and planning clock from the DB; it never modifies observations or starts
work. Universe validity, Settings and schedule policy stay explicit. An oversized
snapshot fails instead of silently truncating. Run the existing provisioned coordinator
and two workers as in DISTRIBUTED, keeping credentials and boot/spool paths unchanged.
No browser/read route imports these scheduling adapters. No polling daemon, automatic
schedule tick, download, source expiry daemon or unattended remeasurement is added.

Admission runs under the same DB lock/transaction as worker authority. It verifies
exact latest retained source UUID/hash/metadata against each refresh reference; a
coverage entry requires no current retained source. Changed history fails the entire
plan and requires a new snapshot. Current DB suppressions override stale files. Issued
attempts without committed receipts block that endpoint for the retained control
history (90 days), even if cancelled or beyond the 24-hour delivery horizon. They are
not converted into ordinary refreshes. New snapshots explicitly count them as blocked.
Control pruning is deliberate loss of that historical guard, never an automatic retry.

Exact schedule replay returns the original campaign UUID, including cancelled/restored
campaigns, and creates no job. Unique schedule identity, all jobs, queue positions and
refresh references commit together. A lost ACK is safe to replay; a pre-commit failure
leaves none. The current one-active-campaign/128-pending/1024-retained-job bounds stay
unchanged, and the executable plan is still at most 32 jobs. Queue/storage failures
reject the whole admission with no secondary spool, partial queue or hidden retries.

A plan expires at the earlier of input clock + lifetime (1–3600 seconds, default 300)
and universe expiry. Execution also respects the Settings campaign timeout. Future
plans fail relative to the coordinator DB clock; use snapshot to avoid host/DB clock
skew. Expiry while committing rolls admission back. After commit, queued/unstarted
expired work cancels; issued expired work becomes uncertain, preserving possible
socket slots through its fixed hard horizon. Original saved results may still recover
delivery-only authority within 24 hours, subject to cancellation/suppression/retention.
Expiry never schedules a replacement measurement. The next explicit refresh has its
own schedule/job/attempt/reserved observation identities and ordinary traffic budget.

## Stop, opt-outs, restart and restore

```sh
uv run --locked netatlas-control stop
uv run --locked netatlas-control status
uv run --locked netatlas-store suppress --network 127.0.0.1/32
# After stopping workers and handling independent copies/current policy:
uv run --locked netatlas-control allow-new-work
```

`stop` atomically persists the global stop switch, increments its generation, cancels
all campaigns/jobs and denies enqueue, permits and delivery. `allow-new-work` only
reopens admission; it cannot uncancel a campaign, revive a lease or clear pacing,
boot generations, suppression or unresolved attempts. Per-campaign `cancel` remains.
Status returns job counts and global_stopped. A stop requires a working DB to commit;
if storage is unavailable, terminate workers locally. Control/heartbeat failure closes
cooperative active sockets under the existing normally-about-three-second bound.
Already-issued 250-ms grants and in-flight connections prevent instantaneous fencing.

Stored suppression now revokes matching jobs in the **same transaction** as source
removal. Claim/heartbeat/permit/delivery also consult it before maintenance. Update
local `opt_out_cidrs` and regenerate plans after a new opt-out; standalone discovery
still needs explicit stop/config update. Delete/quarantine independent worker pending
copies, standalone spools, schedule files, outputs and backups; keep boot.json and
credentials. Offline workers cannot receive deletion. Unlink is not forensic erasure.

Migration 0006 adds schedule identity/input metadata, queue position and source-reference
columns without rewriting observations or shipped migrations. Existing jobs retain
legacy UUID order where positions are zero. Restore to an empty separate DB migrates,
cancels every historical campaign/job, expires leases and **sets global stop**. Keep it
offline until full verification and current suppression reapplication succeed; explicit
allow-new-work is then required. No volume, source identity, password or boot reset.

## Bounds, UDP decision and validation

Universe: 128 nonoverlapping regions, 16 origins/ports, 4096 IPv4 addresses before
expansion, 1024 IPv6 seeds and 16384 candidate endpoints. Input/source snapshot: 4096
summaries, 1024 blocked endpoints/suppressions and 1 MiB serialized operator input or
persisted schedule document. Plans: at most min(128, policy queue, Settings queue),
with one source reference per entry. The separate schedule document does not enlarge
the existing 12-KiB worker campaign snapshot, control HTTP bodies or worker spool.
No new dependency or worker wire schema. Source/raw/outbox/inspection contracts persist.

**UDP remains deferred.** No protocol-specific safe request, response/source-validation,
amplification budget and complete loopback failure corpus has been qualified. Adding
UDP would require another collector/admission contract beyond this TCP scheduling
increment. No DNS/NTP datagrams, raw sockets, multicast, broadcast or new traffic path
were introduced. Existing TCP collectors retain their two connections/two GETs/one
TLS handshake ceilings, no DNS/SNI/authentication/commands and per-connection permits.

`tests/test_scheduler.py` uses independently authored address/count truth for sampling,
IPv6 gaps, fairness, shard partitions, priorities and expiry. PostgreSQL acceptance
covers source identity, negative history, ordered claims/shared grants, changed history,
stop/reopen, atomic suppression, unavailable storage, queue bounds, admission rollback,
lost ACK, unresolved attempts, migration and stopped restore. The existing two-process
HTTP/TLS failure drill also runs via the scheduler and verifies three total permits,
two original sources, two lost delivery ACKs and no extra probes. Full results are in
PROJECT_STATE. No worldwide throughput, real routing accuracy or physical power-failure
qualification follows from this authored experiment.
