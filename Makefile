.PHONY: install run test test-unit lint format typecheck check

install:
	uv sync

run:
	uv run uvicorn pagedoctor.app.main:app --reload

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy --strict src/

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src
	uv run pytest
