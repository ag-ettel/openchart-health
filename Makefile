.PHONY: help lint compliance-lint typecheck test check pipeline export dev-db

help:
	@echo "Available targets:"
	@echo "  check            Run all checks (lint + compliance-lint + test)"
	@echo "  lint             Run ruff linter"
	@echo "  compliance-lint  Check for prohibited language and color coding"
	@echo "  typecheck        Run mypy strict type checking"
	@echo "  test             Run pytest with coverage"
	@echo "  pipeline         Run full pipeline"
	@echo "  export           Re-run export only (no ingest)"
	@echo "  dev-db           Apply Alembic migrations to local dev database"

check: compliance-lint lint test

lint:
	ruff check pipeline/ api/ tests/

compliance-lint:
	python scripts/lint_compliance.py

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
