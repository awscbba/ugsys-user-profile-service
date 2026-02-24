# ugsys-user-profile-service task runner
set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

install-hooks:
    bash scripts/install-hooks.sh

sync:
    uv sync --extra dev

lint:
    uv run ruff check src/ tests/

format:
    uv run ruff format src/ tests/

format-check:
    uv run ruff format --check src/ tests/

typecheck:
    uv run mypy src/

test:
    uv run pytest tests/ -v --tb=short

test-unit:
    uv run pytest tests/unit/ -v --tb=short

test-cov:
    uv run pytest tests/unit/ -v --cov=src --cov-report=term-missing

dev:
    uv run uvicorn src.main:app --reload --port 8002

branch name:
    git checkout -b feature/{{name}}
