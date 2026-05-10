"""Tests for scripts/check_ownership_changes.py — pure-Python diff logic.

These tests don't need the database or any CSV archives. The web-search
verifier is also a pure function modulo the API call, so it's tested with
a mocked Anthropic client.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.check_ownership_changes import (
    HIGH_SIGNAL_ROLES,
    PERCENTAGE_SHIFT_THRESHOLD,
    OwnershipKey,
    _index_by_key,
    _parse_pct,
    _summarize_clusters,
    diff_ownership,
    roll_up_by_facility,
    verify_via_web_search,
)


class TestParsePct:
    def test_plain_int(self):
        assert _parse_pct("50") == 50

    def test_with_percent_sign(self):
        assert _parse_pct("100%") == 100

    def test_decimal(self):
        assert _parse_pct("12.5") == 12

    def test_not_applicable_returns_none(self):
        assert _parse_pct("NOT APPLICABLE") is None
        assert _parse_pct("NO PERCENTAGE PROVIDED") is None

    def test_empty(self):
        assert _parse_pct("") is None
        assert _parse_pct("   ") is None


class TestIndexByKey:
    def test_indexes_by_full_key(self):
        rows = [
            {
                "facility_id": "015009",
                "owner_name": "ACME LLC",
                "role": "5% OR GREATER DIRECT OWNERSHIP INTEREST",
                "owner_type": "Organization",
                "ownership_percentage": "100%",
                "association_date": "since 06/01/2024",
            },
        ]
        idx = _index_by_key(rows)
        key = OwnershipKey("015009", "ACME LLC", "5% OR GREATER DIRECT OWNERSHIP INTEREST")
        assert key in idx
        assert idx[key]["percentage"] == 100
        assert idx[key]["owner_type"] == "Organization"
        assert idx[key]["association_date_raw"] == "since 06/01/2024"

    def test_zero_pads_provider_id(self):
        rows = [{"facility_id": "1009", "owner_name": "X", "role": "ROLE"}]
        idx = _index_by_key(rows)
        assert OwnershipKey("001009", "X", "ROLE") in idx

    def test_role_uppercased(self):
        rows = [{"facility_id": "015009", "owner_name": "X", "role": "operational/managerial control"}]
        idx = _index_by_key(rows)
        assert OwnershipKey("015009", "X", "OPERATIONAL/MANAGERIAL CONTROL") in idx

    def test_skips_rows_missing_required_fields(self):
        rows = [
            {"facility_id": "015009", "owner_name": "", "role": "ROLE"},
            {"facility_id": "", "owner_name": "X", "role": "ROLE"},
            {"facility_id": "015009", "owner_name": "X", "role": ""},
        ]
        assert _index_by_key(rows) == {}


class TestDiffOwnership:
    def _row(self, facility_id, owner_name, role, percentage=None, association="since 01/01/2020"):
        return {
            "facility_id": facility_id,
            "owner_name": owner_name,
            "role": role,
            "owner_type": "Organization",
            "ownership_percentage": str(percentage) + "%" if percentage is not None else "",
            "association_date": association,
        }

    def test_added_record(self):
        prev = _index_by_key([])
        curr = _index_by_key([
            self._row("015009", "ACME LLC", "OPERATIONAL/MANAGERIAL CONTROL")
        ])
        meta = {"015009": {"name": "Burns NH", "state": "AL"}}
        changes = diff_ownership(prev, curr, meta)
        assert len(changes) == 1
        assert changes[0].change_type == "ADDED"
        assert changes[0].owner_name == "ACME LLC"
        assert changes[0].high_signal is True
        assert changes[0].facility_name == "Burns NH"

    def test_removed_record(self):
        prev = _index_by_key([
            self._row("015009", "ACME LLC", "OPERATIONAL/MANAGERIAL CONTROL")
        ])
        curr = _index_by_key([])
        changes = diff_ownership(prev, curr, {})
        assert len(changes) == 1
        assert changes[0].change_type == "REMOVED"

    def test_percentage_shift_above_threshold(self):
        prev = _index_by_key([self._row("015009", "X", "5% OR GREATER DIRECT OWNERSHIP INTEREST", percentage=20)])
        curr = _index_by_key([self._row("015009", "X", "5% OR GREATER DIRECT OWNERSHIP INTEREST", percentage=100)])
        changes = diff_ownership(prev, curr, {})
        assert len(changes) == 1
        assert changes[0].change_type == "PERCENTAGE_SHIFT"
        assert changes[0].previous_percentage == 20
        assert changes[0].current_percentage == 100

    def test_percentage_shift_below_threshold_ignored(self):
        # A 10pp shift is below the PERCENTAGE_SHIFT_THRESHOLD (25)
        assert PERCENTAGE_SHIFT_THRESHOLD > 10
        prev = _index_by_key([self._row("015009", "X", "5% OR GREATER DIRECT OWNERSHIP INTEREST", percentage=50)])
        curr = _index_by_key([self._row("015009", "X", "5% OR GREATER DIRECT OWNERSHIP INTEREST", percentage=60)])
        changes = diff_ownership(prev, curr, {})
        assert changes == []

    def test_low_signal_role_marked_low_signal(self):
        prev = _index_by_key([])
        curr = _index_by_key([self._row("015009", "X", "DIRECTOR")])
        changes = diff_ownership(prev, curr, {})
        assert len(changes) == 1
        assert changes[0].high_signal is False

    def test_high_signal_roles_constant(self):
        # Sanity: the constant captures what we expect
        assert "OPERATIONAL/MANAGERIAL CONTROL" in HIGH_SIGNAL_ROLES
        assert "5% OR GREATER DIRECT OWNERSHIP INTEREST" in HIGH_SIGNAL_ROLES
        assert "DIRECTOR" not in HIGH_SIGNAL_ROLES

    def test_parent_group_attached_when_provided(self):
        prev = _index_by_key([])
        curr = _index_by_key([self._row("015009", "X", "OPERATIONAL/MANAGERIAL CONTROL")])
        groups = {"X": "Big Healthcare Holdings"}
        changes = diff_ownership(prev, curr, {}, parent_groups=groups)
        assert changes[0].parent_group_name == "Big Healthcare Holdings"


class TestRollUpByFacility:
    def test_groups_and_orders_high_signal_first(self):
        from scripts.check_ownership_changes import ChangeRecord
        recs = [
            ChangeRecord("015009", None, None, "ADDED", "DIRECTOR", "X", None, False),
            ChangeRecord("015009", None, None, "ADDED", "OPERATIONAL/MANAGERIAL CONTROL", "Y", None, True),
        ]
        out = roll_up_by_facility(recs)
        assert list(out["015009"][0].role for _ in [0]) == ["OPERATIONAL/MANAGERIAL CONTROL"]
        # First should be the high-signal one
        assert out["015009"][0].high_signal is True


class TestSummarizeClusters:
    def _make_change(self, ccn, owner, role="OPERATIONAL/MANAGERIAL CONTROL",
                    change_type="ADDED", parent=None, state="AL"):
        from scripts.check_ownership_changes import ChangeRecord
        return ChangeRecord(
            provider_id=ccn, facility_name=f"Facility {ccn}", facility_state=state,
            change_type=change_type, role=role, owner_name=owner, owner_type="Organization",
            high_signal=role in HIGH_SIGNAL_ROLES, parent_group_name=parent,
        )

    def test_three_facility_minimum(self):
        # Two facilities of same entity should NOT form a cluster
        recs = [self._make_change("015001", "X"), self._make_change("015002", "X")]
        clusters = _summarize_clusters(recs)
        assert clusters == []

    def test_three_facility_cluster_emerges(self):
        recs = [self._make_change(f"01500{i}", "X") for i in range(1, 4)]
        clusters = _summarize_clusters(recs)
        assert len(clusters) == 1
        assert clusters[0]["facility_count"] == 3
        assert clusters[0]["label"] == "X"
        assert clusters[0]["change_type"] == "ADDED"

    def test_clusters_sorted_descending_by_size(self):
        recs = (
            [self._make_change(f"015{i:03d}", "BigCo") for i in range(10)]
            + [self._make_change(f"025{i:03d}", "SmallCo") for i in range(3)]
        )
        clusters = _summarize_clusters(recs)
        assert [c["label"] for c in clusters] == ["BigCo", "SmallCo"]

    def test_parent_group_folds_entities_into_one_cluster(self):
        # Two distinct entity names share one parent group
        recs = (
            [self._make_change(f"015{i:03d}", "ACME LLC", parent="ACME Holdings") for i in range(2)]
            + [self._make_change(f"025{i:03d}", "ACME OPS LLC", parent="ACME Holdings") for i in range(2)]
        )
        clusters = _summarize_clusters(recs)
        assert len(clusters) == 1
        assert clusters[0]["label"] == "ACME Holdings"
        assert clusters[0]["facility_count"] == 4

    def test_added_and_removed_are_distinct_clusters(self):
        recs = (
            [self._make_change(f"015{i:03d}", "X", change_type="ADDED") for i in range(3)]
            + [self._make_change(f"025{i:03d}", "X", change_type="REMOVED") for i in range(3)]
        )
        clusters = _summarize_clusters(recs)
        assert len(clusters) == 2
        directions = {c["change_type"] for c in clusters}
        assert directions == {"ADDED", "REMOVED"}

    def test_low_signal_changes_excluded(self):
        recs = [self._make_change(f"015{i:03d}", "X", role="DIRECTOR") for i in range(5)]
        assert _summarize_clusters(recs) == []


class TestVerifyViaWebSearch:
    """Test the parsing of Claude API responses, with the API call mocked."""

    def test_parses_verified_response(self, monkeypatch):
        # Build a fake anthropic client that returns a known structured response.
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = (
            "VERIFIED\n"
            "Acme acquired Burns NH per Sept 2025 press release.\n"
            "SOURCE: https://example.com/press\n"
            "SOURCE: https://example.com/sec"
        )
        response = MagicMock()
        response.content = [text_block]

        client = MagicMock()
        client.messages.create.return_value = response

        fake_anthropic = MagicMock()
        fake_anthropic.Anthropic.return_value = client
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

        result = verify_via_web_search("Burns NH", "AL", "Acme LLC", "ADDED", api_key="x")
        assert result["confidence"] == "VERIFIED"
        assert "Acme acquired Burns NH" in result["summary"]
        assert "https://example.com/press" in result["sources"]
        assert len(result["sources"]) == 2

    def test_parses_unverified_response(self, monkeypatch):
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "UNVERIFIED\nNo corroborating news found."
        response = MagicMock()
        response.content = [text_block]

        client = MagicMock()
        client.messages.create.return_value = response
        fake_anthropic = MagicMock()
        fake_anthropic.Anthropic.return_value = client
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

        result = verify_via_web_search("X", "Y", "Z", "ADDED", api_key="x")
        assert result["confidence"] == "UNVERIFIED"
        assert result["sources"] == []

    def test_handles_api_exception(self, monkeypatch):
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("rate limited")
        fake_anthropic = MagicMock()
        fake_anthropic.Anthropic.return_value = client
        monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

        result = verify_via_web_search("X", "Y", "Z", "ADDED", api_key="x")
        assert result["confidence"] == "ERROR"
        assert "rate limited" in result["summary"]

    def test_skipped_when_anthropic_not_installed(self, monkeypatch):
        # Simulate the import failure path
        monkeypatch.setitem(sys.modules, "anthropic", None)
        # The function imports inside; when the import fails it returns SKIPPED.
        # We have to also pop the cached module to force re-import.
        for mod in list(sys.modules):
            if mod == "anthropic":
                sys.modules[mod] = None
        # The function uses `import anthropic`; setting sys.modules["anthropic"] = None
        # makes the import raise ImportError.
        result = verify_via_web_search("X", None, "Z", "ADDED", api_key="x")
        assert result["confidence"] == "SKIPPED"
