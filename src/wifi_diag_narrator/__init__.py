"""wifi-diag-narrator — narrator + citation guardrail.

Public API (re-exported from submodules per Phase 6 plan 06-03):

- ``EVIDENCE_RULES`` — per-class telemetry-path allowlist (D-NARRATOR-04)
- ``narrate_templated`` — deterministic, no-LLM narrator (D-NARRATOR-03, LLM-05)
- ``narrate`` — Anthropic Haiku 4.5 narrator with Structured Outputs
  (LLM-01/02/04); lazy-imports ``anthropic`` (Pitfall C)
- ``strip_invalid_citations`` — citation guardrail (LLM-03)
- ``is_valid_citation`` — single-item citation validator (LLM-03)

Submodule import paths remain stable
(``from wifi_diag_narrator.templated import narrate_templated`` etc.) —
this module re-exports the same symbols at the package surface for
ergonomic consumption from the agent and Space.

The Anthropic LLM narrator path requires ``pip install
wifi-diag-narrator[llm]``; the templated narrator is LLM-free and is
what the agent's local-only mode uses (AGENT-05).
"""

from __future__ import annotations

from .anthropic_narrator import narrate
from .citation_validator import is_valid_citation, strip_invalid_citations
from .evidence_rules import EVIDENCE_RULES
from .templated import narrate_templated

__version__ = "0.1.1"

__all__ = [
    "EVIDENCE_RULES",
    "__version__",
    "is_valid_citation",
    "narrate",
    "narrate_templated",
    "strip_invalid_citations",
]
