# Local installation and offline rehearsal

Phase 14 candidate: **0.15.0**, health **14**, migration **0006**. This is a trusted
local synthetic research system. All listeners remain loopback. No hosting account,
public deployment, license grant or real measurement authorization is included.

## Prerequisites and first downloads

Use Git, Make, OpenSSL CLI, uv **0.12.19**, Python **3.14.7**, Node **26.8.1**, npm
**11.19.0**, Docker with Compose, and the pinned native PostgreSQL **18.3** / PostGIS
**3.6.4** image. `.python-version`, `.nvmrc`, `uv.lock`, `web/package-lock.json` and
`docker/Dockerfile.postgis` are the exact inputs. On this Mac, the existing dedicated
Colima `netatlas` profile provides 2 CPUs / 2 GiB / 20 GiB. See ENVIRONMENT for setup.
Inspect `docker context show`, `colima list`, `docker-compose ps` and existing ports
before starting anything. Never reset existing storage or secrets to fix a failure.

Initial acquisition can require Internet access: repository access, tool installers,
Python via uv, npm/Python packages, the PostgreSQL base image and APT packages for
PostGIS, plus Playwright Chromium and Linux browser system libraries. Advisory
audits and GitHub push/CI also require network access. These are dependency/service
requests, never exposure measurements. Image transitive APT inputs and host tools
are not fully pinned. A cold image rebuild is not guaranteed bit-identical.

No additional geography download is needed: the reviewed tiny Fiji/Suva assets and
fictional associations are packaged, with licenses/hashes in MAP_ASSETS. `/docs`
uses FastAPI's external Swagger assets and is **outside the offline walkthrough**.
The explorer, operations dashboard, OpenAPI JSON and local data paths need no CDN.

## New local installation

Clone the existing private repository through already authorized Git access. Do not
publish a fork. In the new checkout, with no conflicting DB port 55432 or app ports
8000/5173/8001:

```sh
make local-build                  # locked installs, wheel/source and web build
npm --prefix web exec -- playwright install chromium
make db-up COMPOSE=docker-compose # fresh secret/volume only on a new installation
make db-migrate
uv run --locked netatlas-store expire
uv run --locked netatlas-store provision-access
make thesis-demo                  # explicit seed, no network measurement
uv run --locked netatlas-store verify
make local-serve
```

Compose-plugin hosts omit `COMPOSE=docker-compose`. Open `http://127.0.0.1:8000`,
paste the printed **dataset_sha256**, then follow DEMONSTRATION. The restricted read
account serves the built assets/API on one origin. Owner commands use the separate
original connection. No auto-seed, automatic scheduler or background daemon runs.
Use Ctrl-C to stop the foreground app. `make db-down` stops the DB while preserving
its volume. Do not remove that volume or replace its password on an ordinary restart.

## Isolated rehearsal beside an existing installation

Use a **new local clone**, fresh dependency directories and a unique Compose project.
On Colima place it under a VM-shared path (for example a new directory under your
home directory), not macOS private /var/folders temporary storage: the latter cannot
mount the password secret into the VM.
Do not copy data/, .env, config/local.toml, services, blobs or worker credentials from
the owner checkout. A local clone uses existing Git objects without a remote fetch:

```sh
git clone --local --no-hardlinks /PATH/TO/NetAtlas /NEW/PATH/NetAtlas-rehearsal
cd /NEW/PATH/NetAtlas-rehearsal
umask 077
export UV_CACHE_DIR="$PWD/.cache/uv"
export npm_config_cache="$PWD/.cache/npm"
make local-build
npm --prefix web exec -- playwright install chromium
make db-init
```

Choose a free port (the recorded rehearsal used **55433**) and a fresh project name.
Create this private `data/rehearsal-compose.yaml` (Compose 2.24.4+ supports !override):

```yaml
services:
  db:
    ports: !override
      - "127.0.0.1:55433:5432"
```

Set **both** environment variables in every rehearsal terminal so backup/restore
subprocesses and Make select the same isolated container. A `-p` flag in one shell
command alone does not propagate to backup helpers:

```sh
export COMPOSE_PROJECT_NAME=netatlas_phase14_rehearsal_UNIQUE
export COMPOSE_FILE="$PWD/compose.yaml:$PWD/data/rehearsal-compose.yaml"
uv run --locked python - <<'PY'
import json
from pathlib import Path
p = Path('data/storage/connection.json')
s = json.loads(p.read_text())
s['port'] = 55433
p.write_text(json.dumps(s))  # fresh rehearsal file only, permissions retained
PY
# When the pinned image is already available, reuse it without a registry/build:
docker-compose up -d --no-build --pull never --wait
make db-migrate
uv run --locked netatlas-store expire
uv run --locked netatlas-store provision-access
make thesis-demo
uv run --locked netatlas-store verify
make local-serve
```

Use `make db-up COMPOSE=docker-compose` for initial image acquisition/build when it
is missing. The different project creates a separate named volume and secret. Never
substitute an owner volume into the override. Stop only this foreground server before
browser acceptance, which owns ports 8000/5173 and refuses existing listeners.

## Offline replay and verification

After successful online setup/build and Chromium installation:

```sh
export UV_OFFLINE=1
export npm_config_offline=true
make setup build smoke
make thesis-demo
make local-serve
```

Offline package modes fail on missing cache entries instead of fetching. `make setup`
reinstalls node_modules and checks the Python environment. A fresh `.venv` can be
recreated from the primed uv cache. Do not delete directories in the owner checkout
for a rehearsal. The image must already exist: use `up --no-build --pull never` offline,
not an uncached `db-up --build`. Chromium may reuse its separately installed browser
cache. Local Docker transport, PostgreSQL and loopback fixture sockets remain necessary.
This is offline operation with acquired prerequisites, not installation on an empty
machine without downloads or proof of a host-wide network air gap.

Full acceptance, after stopping the manual server:

```sh
make check-db COMPOSE=docker-compose
```

This invokes complete `make check`, including real disposable PostgreSQL/restore,
worker/schedule drills and production Chromium/Axe acceptance. Keep logs private.
For a proportionate evaluation recheck (the original full report remains historical):

```sh
uv run --locked python -m netatlas.evaluation --at RECENT_AWARE_UTC --synthetic --measure --repetitions 1 --samples 2 --output data/evaluation-recheck-NEW.json
```

Use a recent aware UTC clock a few seconds in the past, a new ignored output, and
never change normal budgets. See EVALUATION for the full three-repetition protocol.

## Teardown and recovery

Stop owned foreground processes first. With the rehearsal-specific COMPOSE_FILE and
COMPOSE_PROJECT_NAME still set, inspect `docker-compose ps` and `docker-compose config
--volumes`. Only for this disposable rehearsal, `docker-compose down --volumes` removes
its container and newly created volume. Never run this against the owner's project.
Remove the identified disposable checkout and its private outputs after retaining
reviewed presentation material. Unset both Compose variables before owner commands.
Normal tests/evaluation clean their own DBs. Abrupt termination requires identifying
owned `netatlas_test_*` DBs and private temporary copies before targeted cleanup.

If a command fails, stop at that stage and keep generic/private diagnostics. Do not
reset owner state, steal a listener, relax a bound or reuse a stale source/hash to
manufacture success. OPERATIONS covers credential reconciliation and stopped restore.
Actual rehearsal evidence and remaining decisions are in RELEASE_CANDIDATE.
