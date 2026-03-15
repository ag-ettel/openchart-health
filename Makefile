.PHONY: help lint typecheck test pipeline export dev-db

help:
	@echo "Available targets:"
	@echo "  lint        Run ruff linter"
	@echo "  typecheck   Run mypy strict type checking"
	@echo "  test        Run pytest with coverage"
	@echo "  pipeline    Run full pipeline (ingest → normalize → transform → validate → store → export)"
	@echo "  export      Re-run export only (no ingest)"
	@echo "  dev-db      Apply Alembic migrations to local dev database"

lint:
	ruff check pipeline/ api/ tests/

typecheck:
	mypy pipeline/ api/

test:
	pytest

pipeline:
	# Populated at Phase 1 build time
	@echo "Pipeline not yet implemented (Phase 0 in progress)"

export:
	# Populated at Phase 1 build time
	@echo "Export not yet implemented (Phase 0 in progress)"

dev-db:
	alembic upgrade head
