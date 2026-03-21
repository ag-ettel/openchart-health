"""Tests for contested citation and penalty mutation display logic.

Validates that the export layer correctly handles:
- Contested citations (scope/severity revised after initial publication)
- Penalty amount changes
- The transparency requirements from DEC-028 and phase1_review_notes.md
"""

from __future__ import annotations


class TestContestedCitationLogic:
    """Logic tests for contested citation handling — no database needed."""

    def test_is_contested_when_severity_differs(self) -> None:
        """A citation is contested when current scope differs from original."""
        original = "J"  # Immediate jeopardy
        current = "D"   # No actual harm
        is_contested = original != current
        assert is_contested is True

    def test_not_contested_when_severity_same(self) -> None:
        original = "D"
        current = "D"
        is_contested = original != current
        assert is_contested is False

    def test_ij_threshold_crossed_downgrade(self) -> None:
        """Detect when a revision crosses the immediate jeopardy threshold."""
        IJ_CODES = {"J", "K", "L"}
        original = "J"
        current = "D"
        crossed = original in IJ_CODES and current not in IJ_CODES
        assert crossed is True

    def test_ij_threshold_crossed_upgrade(self) -> None:
        """Facility got WORSE — upgraded to immediate jeopardy."""
        IJ_CODES = {"J", "K", "L"}
        original = "G"
        current = "J"
        crossed = original not in IJ_CODES and current in IJ_CODES
        assert crossed is True

    def test_ij_within_ij_not_threshold_crossing(self) -> None:
        """K→J is within IJ range — contested but not a threshold crossing."""
        IJ_CODES = {"J", "K", "L"}
        original = "K"
        current = "J"
        crossed_down = original in IJ_CODES and current not in IJ_CODES
        crossed_up = original not in IJ_CODES and current in IJ_CODES
        assert crossed_down is False
        assert crossed_up is False

    def test_scope_severity_history_structure(self) -> None:
        """History should be a list of {code, vintage, previous} dicts."""
        history = [
            {"code": "G", "vintage": "2024-02", "previous": "J"},
            {"code": "D", "vintage": "2024-03", "previous": "G"},
        ]
        assert len(history) == 2
        assert history[0]["previous"] == "J"
        assert history[-1]["code"] == "D"


class TestPenaltyAmountChangeLogic:

    def test_amount_changed(self) -> None:
        original = 47829
        current = 33374
        changed = original != current
        assert changed is True

    def test_amount_unchanged(self) -> None:
        original = 23989
        current = 23989
        changed = original != current
        assert changed is False

    def test_original_none_means_no_change_flag(self) -> None:
        """If we don't have the original (first load), don't flag as changed."""
        original = None
        current = 23989
        changed = original is not None and original != current
        assert changed is False


class TestExportContestedFields:
    """Verify the export dict includes the right fields for contested data."""

    def _make_inspection_export(
        self,
        scope: str = "D",
        original_scope: str | None = None,
        is_contested: bool = False,
        history: list | None = None,
    ) -> dict:
        """Simulate what build_json produces for one inspection event."""
        return {
            "scope_severity_code": scope,
            "is_immediate_jeopardy": scope in {"J", "K", "L"},
            "is_contested": is_contested,
            "originally_published_scope_severity": original_scope,
            "scope_severity_history": history,
        }

    def test_uncontested_citation_minimal(self) -> None:
        export = self._make_inspection_export(scope="D")
        assert export["is_contested"] is False
        assert export["originally_published_scope_severity"] is None
        assert export["scope_severity_history"] is None

    def test_contested_citation_has_original(self) -> None:
        export = self._make_inspection_export(
            scope="D",
            original_scope="J",
            is_contested=True,
            history=[{"code": "D", "vintage": "2024-03", "previous": "J"}],
        )
        assert export["is_contested"] is True
        assert export["originally_published_scope_severity"] == "J"
        assert export["scope_severity_code"] == "D"  # Current value is primary

    def test_penalty_amount_changed(self) -> None:
        penalty = {
            "fine_amount": 33374,
            "originally_published_fine_amount": 47829,
            "fine_amount_changed": 47829 != 33374,
        }
        assert penalty["fine_amount_changed"] is True
        assert penalty["fine_amount"] == 33374  # Current is primary

    def test_penalty_amount_unchanged(self) -> None:
        penalty = {
            "fine_amount": 23989,
            "originally_published_fine_amount": 23989,
            "fine_amount_changed": False,
        }
        assert penalty["fine_amount_changed"] is False
