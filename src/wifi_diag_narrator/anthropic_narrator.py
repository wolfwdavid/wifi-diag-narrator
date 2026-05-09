"""LLM narrator wrapper — Anthropic Structured Outputs + tenacity retry.

LLM-01: Anthropic Haiku 4.5 + ``messages.parse(output_format=Verdict)`` —
    grammar-constrained against the Pydantic-derived JSON schema; ~99.8%
    schema-compliance reliability per Anthropic's own benchmarks.

LLM-02: Every EvidenceItem.telemetry_path is non-empty (Pydantic-enforced).

LLM-03: Post-call citation guardrail strips invalid citations
    (citation_validator.strip_invalid_citations).

LLM-04: Verdict.headline + Verdict.suggested_fix populated by the LLM
    (max_length=140 on headline per D-VERDICT-06).

D-NARRATOR-07: System prompt wrapped in a cacheable block
    (cache_control={"type": "ephemeral"}) — ~90% input-cost reduction
    when regenerating all 8 cached scenarios in a single run.

D-NARRATOR-08: System prompt = Pydantic JSON schema + EVIDENCE_RULES + 3
    few-shot examples (built once at module import time).

D-NARRATOR-10: tenacity retry with stop_after_attempt(3) + exponential
    backoff (min=1s, max=10s) on Anthropic transient errors only
    (RateLimitError, APIConnectionError, APITimeoutError). Auth and schema
    errors propagate immediately; broad ``Exception`` retry is forbidden
    because it would mask those structural failures.

Pitfall C: ``anthropic`` is lazy-imported inside ``_get_client()``. The
    Phase 4 agent's local-only mode imports only ``narrate_templated`` and
    must NOT pull anthropic transitively. Module top-level keeps no
    ``import anthropic`` statement; the only imports of the SDK happen
    inside function bodies, after which the cached client is reused.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from wifi_diag_schema.verdict import Verdict

from .citation_validator import strip_invalid_citations
from .evidence_rules import EVIDENCE_RULES
from .system_prompt import build_system_prompt

if TYPE_CHECKING:
    # Type-only import — never executed at runtime, so does not violate
    # the lazy-import contract (Pitfall C). mypy / pyright still see types.
    pass

# Module-level client cache. Populated lazily on first narrate() call.
# The mocking strategy in tests/test_narrator.py patches ``_get_client`` so
# the real anthropic SDK is never invoked during unit tests.
_client: Any | None = None

# Build the system prompt once at module import — it doesn't depend on the
# anthropic SDK, just on the schema + rules.
_SYSTEM_PROMPT = build_system_prompt(EVIDENCE_RULES, num_few_shot=3)


def _get_client() -> Any:
    """Lazy-init the Anthropic client (Pitfall C — no top-level import).

    Returns:
        A cached ``anthropic.Anthropic`` instance.
    """
    global _client
    if _client is None:
        import anthropic  # noqa: PLC0415  — lazy on purpose (Pitfall C)

        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def narrate(
    classifier_verdict: Verdict,
    telemetry_window: list[dict[str, Any]],
    *,
    model: str = "claude-haiku-4-5",
    timeout: float = 30.0,
) -> Verdict:
    """Anthropic Haiku 4.5 + Structured Outputs + cache_control + retry.

    The retry decorator must see the *real* anthropic exception classes,
    but the SDK is lazy-imported (Pitfall C). We therefore build the
    decorated inner function inside narrate() so the lazy import has
    already resolved by the time tenacity wires up retry_if_exception_type.

    Args:
        classifier_verdict: Stub Verdict from the classifier (top_class /
            confidence / top_k populated; headline / suggested_fix /
            evidence are stubs the LLM fills in).
        telemetry_window: List of telemetry-frame dicts (most recent last).
        model: Anthropic model name. Default ``claude-haiku-4-5`` (v1 per
            CLAUDE.md; ``claude-sonnet-4-6`` upgrade path).
        timeout: Per-request timeout in seconds (D-NARRATOR-10 — 30s).

    Returns:
        A Verdict with headline / suggested_fix / evidence populated by the
        LLM, with invalid citations stripped (LLM-03).

    Raises:
        anthropic.APIStatusError on non-transient errors (auth, schema, etc.).
        After 3 transient retries exhausted, the final error reraises.
    """
    client = _get_client()

    # Re-import at use site — already resolved by _get_client(); cheap noop.
    import anthropic  # noqa: PLC0415  — lazy on purpose (Pitfall C)

    @retry(
        stop=stop_after_attempt(3),  # D-NARRATOR-10
        wait=wait_exponential(multiplier=1, min=1, max=10),  # D-NARRATOR-10
        retry=retry_if_exception_type(
            (
                anthropic.RateLimitError,
                anthropic.APIConnectionError,
                anthropic.APITimeoutError,
            )
        ),
        reraise=True,
    )
    def _call_with_retry() -> Verdict:
        user_prompt = _build_user_prompt(classifier_verdict, telemetry_window)
        response = client.messages.parse(
            model=model,
            max_tokens=2048,
            timeout=timeout,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # D-NARRATOR-07
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
            output_format=Verdict,  # LLM-01 — Pydantic JSON Schema → grammar-constrained
        )
        return response.parsed_output

    raw_verdict = _call_with_retry()
    return strip_invalid_citations(raw_verdict, telemetry_window)  # LLM-03


def _build_user_prompt(verdict: Verdict, frames: list[dict[str, Any]]) -> str:
    """Compact telemetry framing — the system prompt has the schema + rules,
    so the user message only carries the per-call payload."""
    return (
        f"Classifier predicted: {verdict.top_class} "
        f"(confidence {verdict.confidence:.0%}).\n\n"
        f"Telemetry window ({len(frames)} frames):\n"
        f"{frames}\n\n"
        f"Produce a Verdict per the schema, with citations from the per-class rules."
    )
