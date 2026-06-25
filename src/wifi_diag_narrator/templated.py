"""Templated narrator — D-NARRATOR-03, LLM-05. No LLM, full Verdict shape.

Used by:
- Phase 4 agent local-only mode (default — strongest privacy story).
- Phase 3 narrator wrapper as a fallback if Anthropic is unavailable
  (defense in depth; D-NARRATOR-10 actually says reraise, but the agent
  uses templated as primary).

Output is structurally indistinguishable from LLM output (same Verdict shape):
the agent's local-only verdict UI is the same shape as the Space's LLM-narrated
UI — same drill-down, same evidence list, same headline + fix.

Per-class wording is Claude's discretion within D-NARRATOR-04: the *what to
cite* is locked by EVIDENCE_RULES; the prose around the citations is free.
"""

from __future__ import annotations

from typing import Any

from wifi_diag_schema.enums import DisconnectClass
from wifi_diag_schema.verdict import EvidenceItem, Verdict

from .citation_validator import _resolve_path
from .evidence_rules import EVIDENCE_RULES

# Headlines: max_length=140 (D-VERDICT-06). Curly-brace placeholders are
# rendered with .format(context=...) by narrate_templated.
_HEADLINES: dict[DisconnectClass, str] = {
    "auth_8021x_eap_fail": "Your network's 802.1X authentication failed during {context}.",
    "ap_roam_rekey_fail": "Roaming to a new access point failed during the auth re-key step.",
    "radius_timeout": "The RADIUS server didn't respond — likely overloaded right now.",
    "captive_portal_expiry": (
        "Your captive-portal session expired — sign back in at the network's portal."
    ),
    "mac_randomization_reject": "The network rejected your device's randomized MAC address.",
    "dhcp_lease_churn": "The DHCP server didn't grant your laptop an IP address.",
    "dns_resolver_fail": "Your DNS resolver failed — domain names aren't resolving.",
    "driver_power_save_wake": "Your Wi-Fi driver didn't fully wake up after sleep.",
    "rf_sticky_client": "Your laptop is stuck on a weak access point.",
    "isp_upstream_fail": "Wi-Fi works locally, but the internet upstream is down.",
    "unknown": "We couldn't confidently pinpoint the cause from the signals seen during {context}.",
}

# Suggested fixes: actionable, IT-ticket-ready, no auto-action verbs.
_SUGGESTED_FIXES: dict[DisconnectClass, str] = {
    "auth_8021x_eap_fail": (
        "Re-enter your school/work credentials, or contact IT — your auth "
        "certificate may have expired."
    ),
    "ap_roam_rekey_fail": ("Toggle Wi-Fi off and on; this usually clears stuck roam state."),
    "radius_timeout": (
        "Wait 30 seconds and reconnect — the auth server is probably under heavy load."
    ),
    "captive_portal_expiry": (
        "Open your browser and sign in at the network's captive portal page."
    ),
    "mac_randomization_reject": (
        "On Apple/Windows: change Wi-Fi settings to use the device's hardware MAC for this network."
    ),
    "dhcp_lease_churn": "Contact IT — the DHCP pool may be exhausted.",
    "dns_resolver_fail": (
        "Try changing your DNS server to 1.1.1.1 (Cloudflare) or 8.8.8.8 (Google)."
    ),
    "driver_power_save_wake": (
        "Disable U-APSD/aggressive power-save in your Wi-Fi adapter properties "
        "(Windows: Device Manager → Advanced)."
    ),
    "rf_sticky_client": (
        "Move closer to a stronger access point, or toggle Wi-Fi off and on to force a roam."
    ),
    "isp_upstream_fail": (
        "The Wi-Fi network is fine — the issue is upstream. Try a hotspot or "
        "contact the network admin."
    ),
    "unknown": (
        "Capture a fresh diagnostic during the next disconnect, or share this "
        "report with IT — the current signals are inconclusive."
    ),
}


def narrate_templated(
    classifier_verdict: Verdict,
    telemetry_window: list[dict[str, Any]],
) -> Verdict:
    """Produce a full-Verdict-shape narration without calling any LLM.

    For each path in ``EVIDENCE_RULES[top_class]``, find the most-recent frame
    where the value is non-null and emit an EvidenceItem citing it. Paths
    that are null across the entire window are silently skipped (consistent
    with D-NARRATOR-02 — never cite a null).

    Args:
        classifier_verdict: The classifier's output. Its top_class drives the
            template choice; top_class / confidence / top_k ride through verbatim.
        telemetry_window: List of telemetry-frame dicts (most recent last).

    Returns:
        A Verdict with headline, suggested_fix, and evidence populated by the
        per-class template.
    """
    cls = classifier_verdict.top_class

    # Pick evidence: per-class rule paths, filtered to those non-null in the window.
    candidate_paths = EVIDENCE_RULES[cls]
    evidence: list[EvidenceItem] = []
    for path in candidate_paths:
        # Find a frame where the value is non-null (D-NARRATOR-02), prefer most recent.
        for f in reversed(telemetry_window):
            v = _resolve_path(path, f)
            if v is not None:
                evidence.append(
                    EvidenceItem(
                        telemetry_path=path,
                        claim=f"Observed {path} = {v}",
                    )
                )
                break

    return classifier_verdict.model_copy(
        update={
            "headline": _HEADLINES[cls].format(context="this session"),
            "suggested_fix": _SUGGESTED_FIXES[cls],
            "evidence": evidence,
        }
    )
