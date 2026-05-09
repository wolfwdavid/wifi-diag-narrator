"""Tests for build_system_prompt (D-NARRATOR-08).

The system prompt embeds:
1. The Pydantic-derived JSON schema for Verdict (so Anthropic Structured Outputs
   has the schema ground-truth in-prompt for grammar-constrained generation).
2. EVIDENCE_RULES (so the LLM knows what to cite per class).
3. A few few-shot examples (Claude's discretion).
"""

from __future__ import annotations

from wifi_diag_narrator.evidence_rules import EVIDENCE_RULES
from wifi_diag_narrator.system_prompt import build_system_prompt


def test_schema_in_prompt():
    """The prompt embeds Verdict's JSON schema field names."""
    p = build_system_prompt(EVIDENCE_RULES, num_few_shot=0)
    assert "telemetry_path" in p
    assert "headline" in p


def test_evidence_rules_in_prompt():
    """The prompt embeds at least one literal class slug + one cited path."""
    p = build_system_prompt(EVIDENCE_RULES, num_few_shot=0)
    assert "auth_8021x_eap_fail" in p
    assert "auth_event_class" in p
