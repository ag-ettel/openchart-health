"""Tests for pure-logic helpers in pipeline/store/upsert.py.

Database-bound functions (the actual upsert logic) need integration tests
against a live PG instance — those run separately. These tests cover the
helpers that don't need a database.
"""

from pipeline.store.upsert import _PG_MAX_PARAMS, _safe_batch_size


class TestSafeBatchSize:
    def test_under_param_limit(self):
        # 24 cols × 2700 rows = 64,800 params (under 65,000)
        assert _safe_batch_size(24) == 2708

    def test_respects_target(self):
        # When target is the binding constraint
        assert _safe_batch_size(2, target=1000) == 1000

    def test_clamps_when_too_many_columns(self):
        # 100K columns → 0 by integer division, but we floor at 1
        assert _safe_batch_size(100000) == 1

    def test_zero_columns_returns_target(self):
        assert _safe_batch_size(0) == 5000
        assert _safe_batch_size(0, target=200) == 200

    def test_large_table_under_target(self):
        # 5 cols × 5000 = 25,000 params; well under 65,000 → returns target
        assert _safe_batch_size(5) == 5000

    def test_pg_max_params_constant_below_postgres_hard_limit(self):
        # Postgres hard limit is 65535; we stay safely under
        assert _PG_MAX_PARAMS <= 65535
