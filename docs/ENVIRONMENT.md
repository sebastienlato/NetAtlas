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

## Phase 4 verification — 2026-10-04

Initial main tree was clean and origin was present. Existing Python 3.14.7,
uv 0.12.19, Node 26.8.1 and npm 11.19.0 pins are unchanged. No container runtime or
PostgreSQL client/server was initially installed. Homebrew installed Docker 29.8.2,
Compose 5.6.0, Colima 0.10.3 and Lima 2.2.1. A dedicated `netatlas` Colima VZ profile
uses 2 CPUs / 2 GiB RAM; its requested 12 GiB disk was rounded to 20 GiB. No login
service was enabled. Standalone `docker-compose` was used without editing global
Docker plugin settings. Colima selected its dedicated Docker context.

Local Compose runs PostgreSQL 18.3 with the version and multi-platform digest pinned
in compose.yaml. Generated random local credentials live in ignored private files;
the database is published only on 127.0.0.1:55432. Dependencies are locked SQLAlchemy
2.1.3, Alembic 1.20.0 and psycopg/binary 3.3.6. No collector dependency or traffic
change occurred. The source package includes the migrations and core fingerprint pack.

Real PostgreSQL tests create isolated disposable databases; the backup/restore drill
uses matching clients inside the Compose container. A manual CLI drill additionally
verified synthetic ingest/replay, derivation, outbox, expiry/GC and coordinated restore.
Final check counts are in PROJECT_STATE. Local test data, blobs, secrets, dump files
and generated outputs are ignored; no real observations were ingested or committed.

A full run exposed a remaining intermittent Python 3.14 TLS fixture deallocator
warning despite the Phase 3 two-tick cleanup workaround; a subsequent full
warnings-as-errors run passed, confirming the timing-dependent nature. Phase 4
replaces that fixture's implicit asyncio.Server accept callbacks with an explicitly
owned synchronous accept callback, retained sockets/transports and cancellation/draining. Production
collectors and traffic budgets are unchanged; warnings are not suppressed.

The first Phase 4 Linux CI passed all 41 storage tests but found the TLS/SMTP
fixture's 20 ms greeting window too short for Linux record delivery/shared-runner
scheduling: the documented fallback GET occurred before the SMTP banner. That
fixture now allows a 200 ms greeting window and a 1-second interaction ceiling,
retaining its no-GET assertion. Production defaults, protocol logic and budgets
are unchanged. Final delivery/CI status is identified by Git history and Actions.

## Phase 5 verification — 2026-10-04

Initial main tree was clean with origin present; Python/uv/Node/npm pins remain
unchanged and no Python/web dependency was added. The existing Colima netatlas
profile was stopped at inspection; it was restarted with the existing 2 CPU /
2 GiB / 20 GiB configuration. A private coordinated pre-upgrade backup was saved.

Compose now builds a native architecture image using the same PostgreSQL 18.3
multi-platform digest and pinned `postgresql-18-postgis-3`/scripts packages
`3.6.4+dfsg-2.pgdg13+1`. The upstream PostGIS image documents amd64-only support,
so a small Dockerfile avoids emulation on this arm64 host. Only the docker/ directory
is sent as build context. Existing volume/secret were preserved. No global Docker
plugin installation was needed; standalone Compose used its classic builder fallback.
The server reports PostgreSQL 18.3 and PostGIS 3.6.4, with PROJ network access off.
Transitive APT packages are not fully pinned; see ADR-039 for reproducibility limits.

Migration 0003 and spatial replay passed. Natural Earth v5.1.2 downloads were used
only to produce the ignored Suva/Fiji demo subset with fictional IP mappings.
Tests never download data and use authored synthetic fixtures. Full check-db passed
212 Python / 3 web tests, including Phase 4 archive upgrade and Phase 5 spatial
backup/restore. No Internet target was measured or real observation ingested.

## Phase 6 verification — 2026-10-04

Initial main tree was clean with the existing private origin. Python 3.14.7,
uv 0.12.19, Node 26.8.1 and npm 11.19.0 were verified unchanged; no dependency
was added. Docker 29.8.2 / standalone Compose 5.6.0 and Colima netatlas were already
running. The existing PostgreSQL 18.3/PostGIS 3.6.4 container, volume and secret were
preserved; migration 0004 adds search indexes without source/document rewrites.

Full `make check-db COMPOSE=docker-compose` passed 240 Python / 3 web tests,
lint/types, builds and offline smoke. Search adds 28 cases, including explicit
truth counts/facets, geography/uncertainty, input/private output, retention/suppression,
replay/reindex, old/new migrations and spatial/search backup restore. The benchmark
used 2,048 synthetic endpoints/6,144 sources on Apple M4 Max / macOS arm64, with a
2-CPU/2-GiB Colima VM. Final methodology/results and index size are in
SEARCH_BENCHMARK.md; complete generated plans remain ignored. No Internet target
measurement, real ingestion, OpenSearch, paid service or new runtime was used.

## Phase 14 rehearsal — 2026-10-05

Pinned host tools and the existing Colima profile were inspected and retained. A
fresh isolated clone/uv/npm caches installed locked dependencies, then recreated its
removed dependency directories using offline modes successfully. A distinct Compose
project, new secret/volume/service roles and port 55433 reused the already-acquired
native PostgreSQL/PostGIS image. The first secret mount from macOS private temporary
storage failed; placing only the disposable clone under the VM-shared workspace fixed
it. The rehearsal seeded/verified 16/16/16 sources/fingerprints/enrichments and served
built assets with its restricted read role. See RELEASE_CANDIDATE for actual checks,
source provenance and limitations. No virgin-machine or uncached-image qualification.
