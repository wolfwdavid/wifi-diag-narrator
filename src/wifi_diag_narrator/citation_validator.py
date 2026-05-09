"""Citation validator — D-NARRATOR-02 + LLM-03 hallucination guardrail.

Two checks per citation (D-NARRATOR-02):
1. ``telemetry_path`` is a real TelemetryFrame field per the schema allowlist.
2. The resolved value is non-null in at least one frame of the telemetry window.

Invalid citations are stripped silently (D-NARRATOR-01) — the narrator's
remaining fields (top_class, confidence, top_k, headline, suggested_fix)
are preserved verbatim.
"""

from __future__ import annotations

from typing import Any

from wifi_diag_schema.telemetry import PingContinuity, TelemetryFrame
from wifi_diag_schema.verdict import EvidenceItem, Verdict


def _build_allowlist() -> frozenset[str]:
    """Enumerate all valid TelemetryFrame.* paths (incl. nested ping_continuity.*).

    The allowlist is the privacy contract; if a path isn't here, the LLM
    hallucinated it.
    """
    allowed: set[str] = set()
    for fname in TelemetryFrame.model_fields:
        if fname == "ping_continuity":
            for sub in PingContinuity.model_fields:
                allowed.add(f"ping_continuity.{sub}")
        else:
            allowed.add(fname)
    return frozenset(allowed)


_ALLOWLIST = _build_allowlist()


def _resolve_path(path: str, payload: dict[str, Any]) -> Any | None:
    """Walk a dotted path; return None on any miss."""
    cur: Any = payload
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def is_valid_citation(item: EvidenceItem, frames: list[dict[str, Any]]) -> bool:
    """D-NARRATOR-02: (a) path in allowlist, (b) value non-null in any frame.

    Citation is valid if the value resolves to non-null in AT LEAST ONE frame
    of the window — most fields are partially null across a window, so we
    don't require every frame to have a value.
    """
    if item.telemetry_path not in _ALLOWLIST:
        return False
    for frame in frames:
        v = _resolve_path(item.telemetry_path, frame)
        if v is not None:
            return True
    return False


def strip_invalid_citations(verdict: Verdict, frames: list[dict[str, Any]]) -> Verdict:
    """D-NARRATOR-01: silently filter invalid evidence; preserve everything else.

    Returns a new Verdict (Pydantic models are frozen) with only the valid
    EvidenceItems retained. All other fields ride through verbatim.
    """
    valid = [e for e in verdict.evidence if is_valid_citation(e, frames)]
    return verdict.model_copy(update={"evidence": valid})
