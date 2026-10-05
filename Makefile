.PHONY: setup dev-api dev-web test lint format build check smoke

setup:
	uv sync --locked
	npm --prefix web ci

dev-api:
	uv run --locked netatlas serve

dev-web:
	npm --prefix web run dev

test:
	uv run --locked pytest
	npm --prefix web test
	@if [ "$$NETATLAS_TEST_DB" = "1" ]; then npm --prefix web run test:e2e; fi

lint:
	uv run --locked python -m netatlas.read_api.contract --check
	uv run --locked ruff check .
	uv run --locked ruff format --check .
	uv run --locked mypy src tests
	npm --prefix web run lint
	npm --prefix web run typecheck

format:
	uv run --locked ruff format .
	uv run --locked ruff check --fix .
	npm --prefix web run format

build:
	uv build --no-sources
	npm --prefix web run build

smoke:
	uv run --locked netatlas-schedule --help > /dev/null
	uv run --locked netatlas-control --help > /dev/null
	uv run --locked netatlas-control enqueue --target 192.0.2.1 --port 80 > /dev/null
	uv run --locked netatlas-search --help > /dev/null
	uv run --locked netatlas fingerprint --inspect > /dev/null
	uv run --locked netatlas config-check
	uv run --locked netatlas example > /dev/null
	uv run --locked netatlas schema > /dev/null
	uv run --locked netatlas discover --target 192.0.2.0/30 --port 80 > /dev/null

check: lint test build smoke

# Database acceptance is explicit locally and mandatory in CI.
COMPOSE ?= docker compose

.PHONY: db-init db-up db-down db-migrate check-db

db-init:
	uv run --locked netatlas-store init-local

db-up: db-init
	$(COMPOSE) up -d --build --wait

db-down:
	$(COMPOSE) stop

db-migrate:
	uv run --locked netatlas-store migrate

check-db: db-up
	NETATLAS_TEST_DB=1 $(MAKE) check

.PHONY: demo
# Explicit operator action; creates authored fixtures, never starts measurement.
demo: db-migrate
	uv run --locked python -m netatlas.demo

.PHONY: local-build local-serve
# Foreground, same-origin production assets; provision-access is explicit/no-clobber.
local-build: setup build

local-serve:
	uv run --locked netatlas serve --storage data/storage/services/read --blobs data/storage/blobs --web-root web/dist
