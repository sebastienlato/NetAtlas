# NetAtlas

**Global Internet Exposure Search & Visualization** — an independent university
thesis project that will measure Internet-facing services, preserve the evidence,
and make it searchable by network and geography. No Shodan, Censys, or other
commercial search database is used.

## Current delivery

Phase 11 adds reproducible offline sampling/sharding over authored routing fixtures,
seed-only IPv6, prefix fairness and explicit source-bound refresh scheduling. A narrow
loopback adapter preserves shared worker budgets, durable stop/suppression and original
measurement identities. See [scheduling and coverage semantics](docs/SCHEDULING.md).
UDP and live routing remain deferred. Package **0.12.0**, migration **0006**.

Phase 10 added two authenticated local worker processes, durable leases/heartbeats,
centrally budgeted connections and atomic replayable delivery. Workers measure only
explicit authored literal-loopback fixtures; uncertain attempts are never automatically
remeasured. See [worker setup and failure semantics](docs/DISTRIBUTED.md).

Phase 9 added endpoint timelines, protocol inspection, bounded inert previews,
unverified certificate assertions and exact confidence/evidence traces to the local
geographic explorer with exact country/region/city place
search, MapLibre page clusters, categorized results, provenance and uncertainty.
The offline Fiji map and explicit synthetic seed use no paid services or external
browser resources. **Discovery defaults to preview; durable ingestion accepts
synthetic fixtures only.** Read requests cannot initiate scans. Inspection preserves
canonical evidence and enforces a separate synthetic preview policy. No Internet
campaign has run. See [inspection and preview policy](docs/INSPECTION.md),
[the explorer/demo guide](docs/GEOGRAPHIC_UI.md),
[asset licenses](docs/MAP_ASSETS.md), [API policy](docs/API.md), [search](docs/SEARCH.md),
[benchmark](docs/SEARCH_BENCHMARK.md), [enrichment](docs/ENRICHMENT.md) and [storage](docs/STORAGE.md).

## Start locally

Prerequisites: Git, Make, [uv](https://docs.astral.sh/uv/), Node **26.8.1** and npm
**11.19.0**. Python **3.14.7** is pinned in `.python-version`; uv can provision it.
Use `nvm install && nvm use` if nvm is available. Offline and loopback checks need no database. PostgreSQL/PostGIS integration checks additionally
require a Docker-compatible engine and Compose; no paid service or external account
is needed. Local database credentials are generated privately.
The OpenSSL CLI is required by TLS tests to generate ephemeral synthetic certificates
and keys in temporary directories. Install dependencies once:

```sh
make setup
make check
# For full browser/database acceptance after local DB setup:
npm --prefix web exec -- playwright install chromium
make check-db COMPOSE=docker-compose
```

Start the two components in separate terminals from the repository root:

```sh
make dev-api
```

```sh
make dev-web
```

Open <http://127.0.0.1:5173>. The web development server proxies `/healthz` and
`/api` to the API on port 8000. API documentation is at
<http://127.0.0.1:8000/docs>. Run `make demo` after database setup and paste its printed dataset hash for the offline
exploration example. See [the guide](docs/GEOGRAPHIC_UI.md). Stop either process with Ctrl-C. Stored-data routes require the local database and `X-NetAtlas-Read: 1` header;
see [API.md](docs/API.md) for the bounded JSON request contract. Health and the static
example do not need the database. The API does not auto-reload; restart after Python changes. Vite reloads web edits automatically.

| Command | Purpose |
| --- | --- |
| `make setup` | Install locked Python and web dependencies |
| `make test` | Python discovery/contract/config/API tests and web component tests |
| `make lint` | Contract drift check, Ruff, formatting, strict mypy, Biome/TypeScript |
| `make format` | Apply Python/web lint fixes and formatting |
| `make build` | Build Python wheel/source archive and static web assets |
| `make smoke` | Exercise offline CLI commands |
| `make check` | Lint, tests, builds, and CLI smoke; DB tests opt in |
| `make check-db` | Start local Compose; full check including PostgreSQL/restore acceptance |
| `uv run --locked netatlas-search --help` | Private local search with bounded JSON query/output |
| `uv run --locked netatlas-enrich --help` | Offline dataset inspection, exact place lookup and enrichment |
| `uv run --locked netatlas-schedule --help` | Offline plans, explicit DB snapshots, lab enqueue and coverage reports |
| `uv run --locked netatlas-control --help` | Separate authenticated local worker/control commands |
| `make demo` | Append authored demo fixtures; print the exact dataset hash to paste into the UI |
| `make db-migrate` | Apply packaged Alembic migrations to the local database |
| `uv run --locked netatlas config-check` | Validate defaults and print configuration digest |
| `uv run --locked netatlas example` | Print a synthetic observation; performs no measurement |
| `uv run --locked netatlas schema` | Print observation JSON Schema |
| `uv run --locked netatlas discover --target 192.0.2.1 --port 80` | Preview explicit scope and policy without connecting |
| `uv run --locked netatlas fingerprint --inspect` | Inspect the bundled offline rule pack |
| `uv run --locked netatlas --version` | Print package version |

For customization, copy `config/default.toml` to ignored `config/local.toml`:

```sh
uv run --locked netatlas --config config/local.toml config-check
NETATLAS_CONFIG=config/local.toml make dev-api
```

Precedence is built-in defaults, then the explicit `--config` file (or
`NETATLAS_CONFIG` when no CLI file is given). Files may override a subset of fields.
There is no implicit working-directory config load or `.env` reader. Unknown keys
and invalid values fail validation; explicit missing files are errors. Configuration
version 3 permits enabled measurement only with validated operator identity; dialing
also requires `discover --measure`. See [the discovery guide](docs/DISCOVERY.md) for
exact bounds, exclusions/opt-outs, reproducibility, cancellation and explicit loopback
fixture steps. Protocol capture additionally requires `measurement.protocol_evidence = true`;
see [protocol evidence](docs/PROTOCOL_EVIDENCE.md) for preview costs, limits, schema
compatibility and coverage gaps. The API binds to loopback only and cannot trigger
scans. If changing its port, also update the development proxy in `web/vite.config.ts`.

## Repository guide

| Path | Responsibility |
| --- | --- |
| `src/netatlas/` | Domain/evidence models, config, discovery, collectors, derivations, spool, enrichment, storage pipeline, search, authenticated worker control plane, offline scheduler, CLI/API |
| `web/` | React/TypeScript geographic explorer, offline MapLibre assets and typed read client |
| `tests/` | Offline Python tests; web tests live beside web code |
| `config/default.toml` | Documented default configuration |
| `docs/` | Data contracts, environment record, and next-phase kickoff |
| `.github/workflows/ci.yml` | Same quality checks on GitHub |

Read [PROJECT_STATE.md](PROJECT_STATE.md) first in a fresh chat, followed by
[ROADMAP.md](ROADMAP.md), [ARCHITECTURE.md](ARCHITECTURE.md), and
[DECISIONS.md](DECISIONS.md). [CONTRIBUTING.md](CONTRIBUTING.md) defines the one-phase
workflow; [SECURITY.md](SECURITY.md) defines measurement and data handling rules.

## Planned stack and cost

Python asyncio workers and FastAPI; Pydantic contracts; PostgreSQL as the local
source of truth with PostGIS points/boundaries and indexed search. OpenSearch is
deferred by the local benchmark. React/TypeScript/Vite and MapLibre serve the local geographic explorer. Start with
bounded local fixtures, private file output and local durable ingestion. Deploy extra services only when the phase
requires them. Dataset and infrastructure details are in the architecture.

Local development and a thesis demonstration require no paid services. Continuous
worldwide collection is a separate capacity problem requiring bandwidth, compute,
storage, suitable hosting/network policy, and operational staffing. No worldwide
performance or coverage claim is made by this bounded local engine.

No project redistribution license has been selected. Keep the repository
private pending the owner's/university's publication and licensing decision. This
does not block implementation; dependency and dataset licenses still apply.
