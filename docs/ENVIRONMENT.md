# Phase 0 environment record

Inspected 2026-10-04 in the initially empty project root.

| Component | Observed |
| --- | --- |
| OS / architecture | macOS / Darwin arm64 |
| Git | 2.54.0 |
| GitHub CLI | 2.92.0, authenticated; no NetAtlas repository existed at inspection |
| Make | GNU Make 3.81 |
| uv | 0.12.19 |
| Project Python | uv-managed CPython 3.14.7, already available |
| Other inspected Python | system/framework 3.14.4; uv also had 3.12.14 |
| Node | 26.8.1 |
| npm | 11.19.0 |
| Go | Not installed; not needed for selected foundation |
| Docker | Not installed; not needed until database/container phases |

The project pins the verified Python and Node versions. Dependency versions are
recorded in lockfiles rather than copied here. No credentials, absolute workstation
paths, machine IDs, measured data, or environment dumps are needed for reproduction.
Future sessions should verify their own environment rather than assuming this
snapshot still describes the host. CI runs on Linux with the same runtime pins.


## Phase 1 verification — 2026-10-04

The same Python 3.14.7, uv 0.12.19, Node 26.8.1 and npm 11.19.0 remain available;
GitHub CLI 2.92.0 and the existing origin on `main` are present. The initial working
tree was clean. No dependency/service installation or runtime upgrade was needed;
the lock changes only the local NetAtlas package to 0.2.0. Local IPv4 and IPv6
loopback fixtures work. On macOS a bound, non-listening TCP socket may time out;
the refusal fixture closes its reserved socket before connecting. Linux CI verifies
the same checks. No public Internet endpoint was used as a measurement fixture.

## Phase 2 verification — 2026-10-04

The initial working tree on `main` was clean. Python 3.14.7, uv 0.12.19,
Node 26.8.1 and npm 11.19.0 were verified again. Baseline `make check` passed
28 Python and 3 web tests. No dependency/runtime upgrade was needed; `uv.lock`
changes only the local package to 0.3.0. TLS tests use the locally available
OpenSSL CLI (3.6.2 on this host), generating keys/certificates in temporary test
folders. They do not require committed keys, a CA account, DNS, network services,
or a paid API. CI's Linux OpenSSL supplies the same fixture-generation commands.
Final validation is recorded in PROJECT_STATE; Git/Actions hold delivery status.

The first Phase 2 Linux CI run passed all 39 protocol tests but exposed timing
sensitivity in the earlier cancellation fixture's 200 ms campaign deadline. Its
deadline case now allows 2 seconds; explicit event/task cases have a 10-second
ceiling and all retain the same completed/incomplete, bounded queue, no-new-work
and cleanup assertions. This gives cold manifest/filesystem startup room without
changing production timing or relaxing traffic limits.

## Phase 3 verification — 2026-10-04

Initial main tree was clean, origin remained the private GitHub repository.
Project Python 3.14.7, uv 0.12.19, Node 26.8.1 and npm 11.19.0 were verified.
Baseline `make check` passed 67 Python and 3 web tests. No dependency or runtime
upgrade was needed; uv.lock changes only NetAtlas to 0.4.0. Tests use synthetic
strings/documentation addresses and existing loopback fixtures. Product-signature
primary references were read as documentation, never used as measurement targets.
Final validation and limitations are in PROJECT_STATE; Git/Actions identify delivery.

The first Phase 3 full run found an intermittent pre-existing TLS fixture shutdown
warning. Ready accept callbacks and their transport-creation tasks now drain before
listener close, so Python 3.14 does not attach accepted transports to an already
closed server. No production networking change or warning filter was introduced.
