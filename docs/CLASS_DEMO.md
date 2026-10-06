# Try NetAtlas locally

NetAtlas is a university research demonstration. This walkthrough uses authored
sample services and fictional IP-to-location associations on an offline Fiji map.
It does not scan the Internet. No API key, hosting account or paid dataset is needed.

## Install once

Use macOS or Linux with Git, Make, OpenSSL, uv **0.12.19**, Node **26.8.1**, npm
**11.19.0**, and a running Docker engine with Compose. Python **3.14.7** is pinned;
uv can download it. Native Windows is not qualified; use a Linux environment.
Initial package and container downloads require Internet access.

```sh
git clone https://github.com/sebastienlato/NetAtlas.git
cd NetAtlas
# If you use nvm: nvm install && nvm use
make local-build
make db-up
make db-migrate
uv run --locked netatlas-store provision-access
make thesis-demo
uv run --locked netatlas-store verify
make local-serve
```

For standalone Compose, use `make db-up COMPOSE=docker-compose`. On macOS with
Colima, start your Docker profile first and keep the clone under a shared home
directory. See [installation](INSTALLATION.md) for prerequisites and isolated setups.
These commands assume a new checkout/database and free ports 55432 and 8000.
Do not delete existing credentials or volumes if a command fails.

Open **http://127.0.0.1:8000**. Copy the `dataset_sha256` printed by `make thesis-demo`
into the dataset field, then search. Keep the terminal running.

## Five things to try

1. Search the default current-attempt view: a fresh thesis seed has **15 endpoints,
   15 observations, 13 candidate records and 11 mapped points**.
2. Look up **Suva** or **Fiji** and use the returned place selection to filter.
3. Open **192.0.2.1:80** and its timeline: the latest negative attempt and older
   evidence are distinct. Reads never initiate collection.
4. Inspect **203.0.113.15:80** for ambiguous product candidates and evidence traces;
   inspect **203.0.113.14:80** for stale evidence and **203.0.113.16:80** for a closed service.
5. Open **http://127.0.0.1:8000/operations** and refresh the aggregate status.

The map covers Fiji, not global device locations. Unknowns, approximate geography
and unverified certificate assertions are intentional. Views clear when hidden or
after 60 seconds; run the search again. Dataset validity lasts seven days after
seeding. A repeated seed appends history, so use a fresh isolated setup if exact
walkthrough counts matter. [DEMONSTRATION](DEMONSTRATION.md) has the full speaking guide.

## Stop and resume

Press Ctrl-C in the app terminal, then `make db-down`. Data is retained.
To resume: `make db-up`, `uv run --locked netatlas-store expire`, then
`make local-serve`. Reuse the original dataset hash while valid. Run
`make thesis-demo` again when it expires and use the newly printed hash; historical
counts will increase. Provision service accounts only on the first setup.

## Verify your installation

Stop the manual app before running browser tests, which use port 8000:

```sh
npm --prefix web exec -- playwright install chromium
make check-db
```

Linux may need `playwright install --with-deps chromium` for browser system
libraries. Use `COMPOSE=docker-compose` with `make check-db` when appropriate.
The complete checks exercise disposable synthetic databases, loopback protocol
fixtures, browser interactions and security boundaries. Plain `make check` skips
database/browser acceptance unless explicitly enabled.

The source is shared publicly for review. No project open-source license has been
selected. [SECURITY](../SECURITY.md) explains reporting and safe local operation.
Do not expose the local API, database or worker service with a tunnel or public port.
