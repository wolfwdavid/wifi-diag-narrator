"""Tests for narrate_templated (D-NARRATOR-03, LLM-05).

The templated narrator's output must be structurally indistinguishable from
LLM output (same Verdict shape) so the agent's local-only mode (Phase 4)
produces a UI experience identical to the Space's LLM-narrated path.
"""

from __future__ import annotations

from typing import get_args

from wifi_diag_schema.enums import DisconnectClass
from wifi_diag_schema.verdict import Verdict

from wifi_diag_narrator.evidence_rules import EVIDENCE_RULES
from wifi_diag_narrator.templated import (
    _HEADLINES,
    _SUGGESTED_FIXES,
    narrate_templated,
)

# A representative classifier-output stub that the narrator will fill in.
_STUB = Verdict(
    top_class="auth_8021x_eap_fail",
    confidence=0.85,
    top_k=[("auth_8021x_eap_fail", 0.85)]
    + [(c, 0.0) for c in get_args(DisconnectClass) if c != "auth_8021x_eap_fail"],
    headline="stub",
    suggested_fix="stub",
    evidence=[],
)
# A telemetry window that has all three EVIDENCE_RULES['auth_8021x_eap_fail'] paths populated.
_FRAMES = [
    {
        "auth_event_class": "8021x_fail",
        "rssi_dbm": -65,
        "dns_resolution_ms": None,
        "ping_continuity": {"packet_loss_pct": 30.0, "avg_rtt_ms": 850.0},
    }
]


def test_full_verdict_shape():
    """narrate_templated returns a fully-populated Verdict."""
    v = narrate_templated(_STUB, _FRAMES)
    assert isinstance(v, Verdict)
    assert len(v.headline) > 0
    assert len(v.suggested_fix) > 0
    assert len(v.evidence) >= 1


def test_shape_matches_llm():
    """The classifier's fields ride through unchanged; only the narrator-fillable
    fields (headline / suggested_fix / evidence) are populated."""
    v = narrate_templated(_STUB, _FRAMES)
    assert v.top_class == _STUB.top_class
    assert v.confidence == _STUB.confidence
    assert v.top_k == _STUB.top_k


def test_uses_evidence_rules_for_class():
    """All evidence telemetry_paths come from EVIDENCE_RULES[top_class]."""
    v = narrate_templated(_STUB, _FRAMES)
    allowed = set(EVIDENCE_RULES["auth_8021x_eap_fail"])
    assert all(e.telemetry_path in allowed for e in v.evidence)


def test_skips_paths_with_null_values():
    """A path in EVIDENCE_RULES[cls] whose value is null in every frame is skipped."""
    stub = _STUB.model_copy(
        update={
            "top_class": "captive_portal_expiry",
            "top_k": [("captive_portal_expiry", 1.0)]
            + [(c, 0.0) for c in get_args(DisconnectClass) if c != "captive_portal_expiry"],
        }
    )
    # captive_portal_detected and network_mode have values; dns_resolution_ms is null.
    frames_partial = [
        {
            "captive_portal_detected": False,
            "dns_resolution_ms": None,
            "network_mode": "captive",
        }
    ]
    v = narrate_templated(stub, frames_partial)
    assert all(e.telemetry_path != "dns_resolution_ms" for e in v.evidence)


def test_headline_within_max_length():
    """All 10 templated headlines (one per class) are <= 140 chars after rendering
    (D-VERDICT-06 schema constraint on Verdict.headline)."""
    for cls, tmpl in _HEADLINES.items():
        rendered = tmpl.format(context="this session")
        assert len(rendered) <= 140, f"{cls}: headline {len(rendered)} chars"


def test_all_classes_have_headline_and_fix():
    """Every DisconnectClass has an entry in both _HEADLINES and _SUGGESTED_FIXES."""
    slugs = set(get_args(DisconnectClass))
    assert set(_HEADLINES.keys()) == slugs
    assert set(_SUGGESTED_FIXES.keys()) == slugs
