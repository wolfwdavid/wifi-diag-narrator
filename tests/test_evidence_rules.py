"""Tests for EVIDENCE_RULES (D-NARRATOR-04).

The schema-allowlist test enforces that every path in EVIDENCE_RULES is a real
TelemetryFrame field — future schema major bumps that drop a field will fail
this test instead of silently breaking the LLM narrator's citations.
"""

from __future__ import annotations

from typing import get_args

from wifi_diag_schema.enums import DisconnectClass
from wifi_diag_schema.telemetry import PingContinuity, TelemetryFrame

from wifi_diag_narrator.evidence_rules import EVIDENCE_RULES

_ALL_SLUGS = set(get_args(DisconnectClass))


def _is_valid_path(p: str) -> bool:
    """A path is valid if it's a top-level TelemetryFrame field
    OR a `ping_continuity.X` where X is in PingContinuity.model_fields.
    """
    if "." in p:
        head, sub = p.split(".", 1)
        if head != "ping_continuity":
            return False
        return sub in PingContinuity.model_fields
    return p in TelemetryFrame.model_fields


def test_all_classes_present():
    """Every DisconnectClass slug has a rule."""
    assert set(EVIDENCE_RULES.keys()) == _ALL_SLUGS


def test_every_path_in_telemetry_allowlist():
    """Every cited path is a real TelemetryFrame field (privacy/correctness contract)."""
    for cls, paths in EVIDENCE_RULES.items():
        for p in paths:
            assert _is_valid_path(p), f"{cls}: path {p!r} not in TelemetryFrame allowlist"


def test_no_empty_rules():
    """Every class has at least 2 cited paths so the templated narrator has material."""
    for cls, paths in EVIDENCE_RULES.items():
        assert len(paths) >= 2, f"{cls} has only {len(paths)} rule(s)"
