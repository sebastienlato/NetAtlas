# Bounded discovery — through Phase 2

`netatlas discover` is an offline preview unless **both** `--measure` and a valid
`measurement.enabled = true` configuration are supplied. Targets and ports are
mandatory, explicit and repeatable; hostnames, URLs, zone IDs, port ranges and
CIDRs with host bits are rejected. Dry runs create no spool and open no sockets.

```sh
uv run --locked netatlas discover --target 192.0.2.0/30 --target 2001:db8::/126 --port 80 --seed 42
uv run --locked netatlas discover --lab-loopback --target 127.0.0.1 --port 8080
```

Documentation addresses in the first example are denied in production. The second
only previews a loopback fixture; lab mode never permits private networks, arbitrary
127/8 addresses, CIDRs, mapped IPv6 loopback, or mixed production/lab scope.

## Explicit local fixture measurement

Start a fixture you control on loopback, for example in a separate terminal:

```sh
uv run --locked python -m http.server 8080 --bind 127.0.0.1 --directory tests
```

Copy `config/default.toml` to ignored `config/local.toml`. For this synthetic lab
only, set these fields in its existing `[measurement]` section:

```toml
enabled = true
operator_name = "Fixture Researcher"
operator_contact = "research@example.org"
user_agent = "NetAtlas/0.3 (research; loopback fixture)"
```

```sh
uv run --locked netatlas --config config/local.toml discover --lab-loopback --target 127.0.0.1 --port 8080 --measure
```

Use a real identifiable operator and reachable email or HTTPS contact for separately
authorized real measurements. Contact URLs cannot contain credentials, queries or
fragments. Control characters and invalid node identifiers are rejected. There is
no contact verification request, and connect-only discovery sends no user-agent or
application bytes. Stop the fixture and campaign with Ctrl-C when finished.

## Bounds and policy

| Control | Default | Hard upper bound |
| --- | --- | --- |
| Scope entries | Explicit | 256 |
| Addresses, counted before exclusions/deduplication | 4096 | 4096 |
| Ports, explicit integers 1–65535 | Explicit | 64 (16 in lab) |
| Address × port candidates before deduplication | 16384 | 16384 |
| Concurrent workers | 32 | 128 |
| Queued endpoints | 128 | 256 |
| Global connect starts/second | 10 | 100 |
| Starts/second per /24 IPv4 or /48 IPv6 | 1 | 20 |
| Connect timeout | 3 seconds | 30 seconds |
| Campaign deadline | 300 seconds | 3600 seconds |
| Entries per exclusion, opt-out or allowlist | 0 | 1024 |

Scope arithmetic rejects oversized CIDRs **before enumeration**, including huge
IPv6 ranges and denied ranges. Overlapping networks and duplicate ports are removed
within accepted scope. CIDR expansion includes every address, including the first
and last: subnet host/broadcast semantics cannot be inferred for arbitrary public
prefixes. Special-use and multicast denials still apply to each address.

Networks/ports are deterministically shuffled and each network is traversed from
a seeded cyclic offset. Memory holds the small input, bounded per-prefix timing
state, queue and active workers; no full endpoint list or observation list is built.
One producer may hold one extra endpoint while waiting for queue space. Admission
order is reproducible with the saved seed, scope, algorithm and Python version;
concurrent completion order, UUIDs, timestamps and reachability are not reproducible.

Policy `connect-policy-1` pins the deny prefixes in `discovery/policy.py`, derived
from the [IANA IPv4](https://www.iana.org/assignments/iana-ipv4-special-registry/)
and [IANA IPv6](https://www.iana.org/assignments/iana-ipv6-special-registry/) registries
(last updated 2025-10-09, reviewed 2026-10-04). All registry blocks are denied,
including otherwise global special-purpose exceptions. Contained rows are covered
by their parent block. Multicast, non-global/reserved addresses and IPv6 outside
2000::/3 are also denied. No live routing assurance is claimed. Registry changes
require review, boundary tests, and policy version/hash updates; tests never download data.

`exclusion_cidrs` and `opt_out_cidrs` deny addresses before any allowlist decision,
including loopback fixtures. `allow_cidrs` only narrows eligibility. Settings are
immutable for a campaign. To process a new opt-out, stop the active campaign first,
add its CIDR to local configuration, preview and restart; there is no hot reload.
Retain policy/config hashes and the manifest for the audit trail. No policy override
can turn production special-use addresses into eligible targets.

One shared no-burst pacer applies both global and per-prefix start spacing across
all workers. Late wakeups cannot accumulate a burst. It conservatively serializes
rate admission; one busy prefix can delay other prefixes. Socket concurrency counts
active workers (some may be waiting for admission). Rates bound connect attempts,
not kernel TCP retransmission packets. Every additional protocol connection uses this
same pacer and policy check. No retries occur. An advisory lock prevents
two campaigns in the same spool; separate checkouts/hosts do not share budgets.

## Outcomes, cancellation and files

| Observation outcome | Error code | Meaning |
| --- | --- | --- |
| `open` | null | At least one TCP connection established; protocol results are separate |
| `closed` | `connection_refused` | Explicit ECONNREFUSED; wire-v1 spelling retained |
| `timeout` | `connect_timeout`, `endpoint_timeout` | Deadline or ETIMEDOUT before TCP established; state remains uncertain |
| `error` | `network_unreachable`, `local_permission_denied`, `socket_error` | Attempt failed; no claim that service is closed |

Sockets are owned by a context manager and closed on every return, error and
cancellation. Eligibility is checked again after rate waiting, immediately before
connecting. SIGINT/SIGTERM, cancellation and deadline stop new dialing, cancel
queued/in-flight work, await cleanup, flush completed results and finalize the
manifest. Interrupted attempts do not become fabricated timeout/error observations;
they contribute to `incomplete`. Repeated graceful cancellation cannot interrupt
cleanup. Failed workers cancel siblings and finalize a failed campaign.

Each fresh UUID directory under ignored `data/` contains:

- `observations.jsonl`: schema-v2 observations, one JSON object per completed attempt.
- `manifest.json`: version 2; running/final status, full non-secret effective settings,
  config version/hash, input/preview, policy/registry versions and policy hash,
  seed/order, scanner/software/Python identities, UTC timestamps, attempted/completed/
  incomplete counts, actual connection attempts, outcome counts and final JSONL SHA-256.

Manifest replacement is atomic; output files are mode 0600, campaign directories
0700. Records are flushed synchronously on completion; the JSONL is fsynced at final
handoff. Manifest and spool are local research data, including addresses and operator
contact; never commit them. Console preview intentionally shows supplied scope and
policy. Discovery logs contain generated campaign/observation IDs, outcomes and
counts, with no addresses, contact details, raw exception messages or payloads.

Exit codes: 0 for dry-run/completion; 130 for a graceful stop; 1 for the campaign
deadline; 2 for invalid input, disabled measurement, locked/unwritable spool or
worker failure. A disk failure can prevent final manifest writing; a hard kill or
power loss may leave `running` status and a partial final JSONL line. There is no
resume/replay, transactional storage, filesystem durability guarantee after power
loss, or performance claim. Phase 4 will add durable ingestion. Protocol collection
is an explicit config opt-in; interaction/response settings remain
unused by connect-only work. See [PROTOCOL_EVIDENCE.md](PROTOCOL_EVIDENCE.md) for the
two-connection plan, cumulative caps and deadlines. Set `protocol_evidence = true` in
the existing measurement section to preview/collect protocols; config version is 3.

Tests use synthetic policy arithmetic, fake clocks/connect errors, and explicit
loopback fixture sockets. `make check` includes an offline denied-scope preview.
No Internet scan is part of implementation validation.

## Phase 10 local workers

The standalone command above is unchanged. A separate authenticated local worker
adapter now uses durable central admission, leases and exact-result delivery, described
in [DISTRIBUTED.md](DISTRIBUTED.md). Its enqueue interface remains preview by default
and is narrower: enabled identity, --measure, --synthetic and literal-loopback scope.
Standalone campaigns do not share the distributed budget or consult worker leases;
do not run them alongside a worker campaign as a way to multiply traffic. No distributed
Internet campaign or automatic refresh daemon is implemented. Phase 11 adds separate
offline authored routing/seed plans and explicit loopback refresh admission; see
[SCHEDULING.md](SCHEDULING.md). Its logical shards never multiply worker budgets.
