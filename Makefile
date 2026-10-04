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

lint:
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
	uv run --locked netatlas config-check
	uv run --locked netatlas example > /dev/null
	uv run --locked netatlas schema > /dev/null
	uv run --locked netatlas discover --target 192.0.2.0/30 --port 80 > /dev/null

check: lint test build smoke
