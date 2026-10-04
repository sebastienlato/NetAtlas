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
