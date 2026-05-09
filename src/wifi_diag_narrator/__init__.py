"""wifi-diag-narrator — narrator + citation guardrail.

Public API (populated as modules land in plan 03-04):
- ``EVIDENCE_RULES`` — per-class telemetry-path allowlist (D-NARRATOR-04)
- ``narrate_templated`` — deterministic, no-LLM narrator (D-NARRATOR-03, LLM-05)
- ``is_valid_citation`` / ``strip_invalid_citations`` — citation guardrail (LLM-03)
- ``build_system_prompt`` — system-prompt builder for the LLM narrator

The Anthropic LLM narrator (``anthropic_narrator.narrate``) lazy-imports the
``anthropic`` SDK (Pitfall C); install via ``pip install wifi-diag-narrator[llm]``.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
