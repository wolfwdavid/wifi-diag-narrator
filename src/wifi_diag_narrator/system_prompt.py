"""Build the cacheable system prompt — schema + EVIDENCE_RULES + few-shot.

The whole prompt is wrapped in a single cacheable block via cache_control on
the call site (D-NARRATOR-07) — when narrate() runs across the 8 cached
scenarios in a single regen, the system prefix is read from cache for runs
2-8 (~90% input-cost reduction).

D-NARRATOR-08 layering: Pydantic JSON schema first (grammar ground truth for
Anthropic Structured Outputs), per-class evidence rules next (so the LLM
knows what to cite), few-shot examples last.

Few-shot example selection (Claude's discretion per CONTEXT.md):
- ``auth_8021x_eap_fail`` — the dogfood case (project-owner's school Wi-Fi).
- ``captive_portal_expiry`` — non-enterprise variant (coffee-shop networks).
- ``rf_sticky_client`` — slow-window class (120s window per Phase 1 D-04).
"""

from __future__ import annotations

import json

from wifi_diag_schema.enums import DisconnectClass
from wifi_diag_schema.verdict import Verdict


def build_system_prompt(
    rules: dict[DisconnectClass, list[str]],
    num_few_shot: int = 3,
) -> str:
    """D-NARRATOR-08 — schema + rules + few-shot, in that order.

    Args:
        rules: EVIDENCE_RULES dict mapping each DisconnectClass to its
            cited TelemetryFrame paths.
        num_few_shot: How many few-shot example pairs to include.
            Default 3 (the canonical set from CONTEXT.md Discretion).

    Returns:
        The full system-prompt string. Pass to Anthropic's
        ``messages.parse(system=[{"type": "text", "text": ..., "cache_control": ...}])``.
    """
    schema_json = json.dumps(Verdict.model_json_schema(), indent=2)

    rules_section = "\n".join(f"- {cls}: cite from {rules[cls]}" for cls in rules)

    few_shot_section = _few_shot_examples(num_few_shot)

    return f"""You are a Wi-Fi disconnect diagnosis narrator. You receive
classifier output and a window of telemetry. You produce a Verdict matching
this exact JSON Schema:

{schema_json}

For every evidence claim, you MUST:
1. Set telemetry_path to a real TelemetryFrame field (allowlist enforced).
2. Cite a value that is non-null in the provided telemetry.
3. Use one of the per-class evidence patterns below:

{rules_section}

Examples:

{few_shot_section}

Constraints:
- headline: <=140 chars, plain English, single sentence.
- suggested_fix: actionable, IT-ticket-ready, no auto-action verbs.
- evidence: 3-5 items, each with telemetry_path + claim.
"""


# Few-shot examples — picked per CONTEXT.md Discretion guidance.
_FEW_SHOT_EXAMPLES: list[str] = [
    """\
Example 1 — auth_8021x_eap_fail (school 802.1X dogfood case):

Input: classifier predicted auth_8021x_eap_fail with confidence 0.92.
Telemetry window (most recent frame):
  auth_event_class: "8021x_fail"
  rssi_dbm: -68
  ping_continuity.packet_loss_pct: 100.0

Output Verdict:
{
  "schema_version": "1.1.0",
  "top_class": "auth_8021x_eap_fail",
  "confidence": 0.92,
  "top_k": [["auth_8021x_eap_fail", 0.92]],
  "headline": "Your school's 802.1X authentication failed during this session.",
  "suggested_fix": "Re-enter your school credentials, or contact IT — your auth certificate may have expired.",
  "evidence": [
    {"telemetry_path": "auth_event_class", "claim": "OS reported 802.1X auth failure event"},
    {"telemetry_path": "rssi_dbm", "claim": "Signal was usable (-68 dBm) so this is auth, not RF"},
    {"telemetry_path": "ping_continuity.packet_loss_pct", "claim": "100% packet loss after auth failure cut connectivity"}
  ]
}""",
    """\
Example 2 — captive_portal_expiry (coffee-shop, non-enterprise variant):

Input: classifier predicted captive_portal_expiry with confidence 0.88.
Telemetry window (most recent frame):
  captive_portal_detected: true
  network_mode: "captive"
  dns_resolution_ms: 4500.0

Output Verdict:
{
  "schema_version": "1.1.0",
  "top_class": "captive_portal_expiry",
  "confidence": 0.88,
  "top_k": [["captive_portal_expiry", 0.88]],
  "headline": "Your captive-portal session expired — sign back in at the network's portal.",
  "suggested_fix": "Open your browser and sign in at the network's captive portal page.",
  "evidence": [
    {"telemetry_path": "captive_portal_detected", "claim": "Captive portal redirect detected on this network"},
    {"telemetry_path": "network_mode", "claim": "Network is in captive mode (coffee-shop / hotel pattern)"},
    {"telemetry_path": "dns_resolution_ms", "claim": "DNS resolution slowed to 4500ms (portal interception)"}
  ]
}""",
    """\
Example 3 — rf_sticky_client (slow-window class, 120s window per D-04):

Input: classifier predicted rf_sticky_client with confidence 0.79.
Telemetry window (most recent frame):
  rssi_dbm: -82
  neighbor_ap_count_5ghz: 3
  per_packet_retry_count: 47

Output Verdict:
{
  "schema_version": "1.1.0",
  "top_class": "rf_sticky_client",
  "confidence": 0.79,
  "top_k": [["rf_sticky_client", 0.79]],
  "headline": "Your laptop is stuck on a weak access point.",
  "suggested_fix": "Move closer to a stronger access point, or toggle Wi-Fi off and on to force a roam.",
  "evidence": [
    {"telemetry_path": "rssi_dbm", "claim": "Signal at -82 dBm is poor (threshold for roam ~-75 dBm)"},
    {"telemetry_path": "neighbor_ap_count_5ghz", "claim": "3 stronger APs visible on 5 GHz but client did not roam"},
    {"telemetry_path": "per_packet_retry_count", "claim": "Retry count of 47 confirms degraded link"}
  ]
}""",
]


def _few_shot_examples(n: int) -> str:
    """Return the first ``n`` few-shot example strings, joined by blank lines."""
    return "\n\n".join(_FEW_SHOT_EXAMPLES[:n])
