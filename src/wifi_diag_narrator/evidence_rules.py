"""Per-class evidence rules (D-NARRATOR-04).

Shared by both narrators:
- The templated narrator (``templated.narrate_templated``) iterates these
  paths and emits an EvidenceItem for each one whose value is non-null in
  the telemetry window.
- The LLM narrator's system prompt (``system_prompt.build_system_prompt``)
  embeds this dict so the model knows what to cite per class.

Every path here MUST exist in TelemetryFrame.model_fields (or be a
``ping_continuity.X`` sub-path). Enforced by
``tests/test_evidence_rules.py::test_every_path_in_telemetry_allowlist`` —
schema major bumps that drop a field will fail this test instead of
silently breaking citations.
"""

from __future__ import annotations

from wifi_diag_schema.enums import DisconnectClass

EVIDENCE_RULES: dict[DisconnectClass, list[str]] = {
    "auth_8021x_eap_fail": [
        "auth_event_class",
        "ping_continuity.packet_loss_pct",
        "rssi_dbm",
    ],
    "ap_roam_rekey_fail": [
        "bssid",
        "auth_event_class",
        "rssi_dbm",
        "beacon_rssi_dbm",
    ],
    "radius_timeout": [
        "auth_event_class",
        "ping_continuity.avg_rtt_ms",
        "ping_continuity.packet_loss_pct",
    ],
    "captive_portal_expiry": [
        "captive_portal_detected",
        "dns_resolution_ms",
        "network_mode",
    ],
    "mac_randomization_reject": [
        "mac_randomization_state",
        "auth_event_class",
        "os",
    ],
    "dhcp_lease_churn": [
        "dhcp_event_class",
        "ping_continuity.packet_loss_pct",
    ],
    "dns_resolver_fail": [
        "dns_resolution_ms",
        "ping_continuity.avg_rtt_ms",
    ],
    "driver_power_save_wake": [
        "driver_state",
        "rssi_dbm",
        "per_packet_retry_count",
    ],
    "rf_sticky_client": [
        "rssi_dbm",
        "neighbor_ap_count_5ghz",
        "per_packet_retry_count",
    ],
    "isp_upstream_fail": [
        "ping_continuity.packet_loss_pct",
        "ping_continuity.avg_rtt_ms",
        "dns_resolution_ms",
    ],
}
