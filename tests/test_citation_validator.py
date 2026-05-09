"""Tests for the citation validator (D-NARRATOR-01/02, LLM-03)."""

from __future__ import annotations

from wifi_diag_schema.verdict import EvidenceItem, Verdict

from wifi_diag_narrator.citation_validator import (
    is_valid_citation,
    strip_invalid_citations,
)

# Two representative frames; ping_continuity is nested as the schema requires.
_F1 = {
    "rssi_dbm": -55,
    "dns_resolution_ms": None,
    "ping_continuity": {"packet_loss_pct": 0.0, "avg_rtt_ms": 12.5},
}
_F2 = {
    "rssi_dbm": -60,
    "dns_resolution_ms": 87.0,
    "ping_continuity": {"packet_loss_pct": 5.0, "avg_rtt_ms": None},
}


def test_known_path_passes():
    """A real TelemetryFrame field with non-null value in the window is valid."""
    assert is_valid_citation(EvidenceItem(telemetry_path="rssi_dbm", claim="x"), [_F1, _F2])


def test_unknown_path_rejected():
    """A field not in the schema is rejected (privacy/correctness contract)."""
    assert not is_valid_citation(
        EvidenceItem(telemetry_path="hallucinated_field", claim="x"), [_F1]
    )


def test_null_value_rejected():
    """A real field that's null in every frame is rejected (D-NARRATOR-02)."""
    assert not is_valid_citation(
        EvidenceItem(telemetry_path="dns_resolution_ms", claim="x"),
        [{"dns_resolution_ms": None}],
    )


def test_at_least_one_non_null_passes():
    """If ANY frame has non-null at the path, citation is valid."""
    assert is_valid_citation(
        EvidenceItem(telemetry_path="dns_resolution_ms", claim="x"), [_F1, _F2]
    )


def test_nested_ping_continuity_path():
    """Dotted paths walk through nested ping_continuity dict."""
    assert is_valid_citation(
        EvidenceItem(telemetry_path="ping_continuity.packet_loss_pct", claim="x"),
        [_F1],
    )
    # Null nested value with no other frames → rejected.
    assert not is_valid_citation(
        EvidenceItem(telemetry_path="ping_continuity.jitter_ms", claim="x"),
        [{"ping_continuity": {"jitter_ms": None}}],
    )


def test_strip_silently_filters_invalid():
    """strip_invalid_citations preserves verdict shape; only filters evidence list."""
    v = Verdict(
        top_class="auth_8021x_eap_fail",
        confidence=0.9,
        top_k=[("auth_8021x_eap_fail", 0.9)],
        headline="x",
        suggested_fix="x",
        evidence=[
            EvidenceItem(telemetry_path="rssi_dbm", claim="real"),
            EvidenceItem(telemetry_path="hallucinated", claim="fake"),
            EvidenceItem(telemetry_path="ping_continuity.packet_loss_pct", claim="real"),
        ],
    )
    stripped = strip_invalid_citations(v, [_F1])
    assert len(stripped.evidence) == 2
    assert all(e.telemetry_path != "hallucinated" for e in stripped.evidence)
    # Other fields untouched (D-NARRATOR-01 — strip silently, preserve everything else).
    assert stripped.top_class == v.top_class
    assert stripped.confidence == v.confidence
    assert stripped.top_k == v.top_k
    assert stripped.headline == v.headline
    assert stripped.suggested_fix == v.suggested_fix
