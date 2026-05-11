# wifi-diag-narrator

Templated + Anthropic Haiku 4.5 narrator package for the [AI Internet Diagnostic](https://huggingface.co/WolfDavid/ai-internet-diagnostic-model) project.

> **Supporting infrastructure.** This package supplies the LLM-narrator + citation-validation guardrail used by the Space and the agent. For results-first numbers, architecture, and live demo, see the [Model repo README](https://huggingface.co/WolfDavid/ai-internet-diagnostic-model#results).

## Install

```bash
pip install wifi-diag-narrator
```

## Public API

- `narrate(verdict, telemetry, frames)` — Anthropic Structured Outputs narrator
- `narrate_templated(verdict)` — LLM-free templated narrator (used by agent local-only mode)
- `strip_invalid_citations(narration)` — citation-guardrail enforcer

See the [Model repo](https://huggingface.co/WolfDavid/ai-internet-diagnostic-model) for the architecture diagram and full pipeline context.

---

# wifi-diag-narrator

Narrator + citation guardrail for [AI Internet Diagnostic](https://github.com/WolfDavid/ai_internet_diagnostic).

Two narrators with the same `Verdict` output shape:

- **`narrate_templated(verdict, frames)`** — deterministic, no network egress. Used by the agent's local-only mode (Phase 4) and as a fallback. Always returns a full `Verdict` (LLM-05).
- **`narrate(verdict, frames, model="claude-haiku-4-5")`** — Anthropic Haiku 4.5 with Structured Outputs (Pydantic-derived JSON schema), tenacity retry, prompt caching (D-NARRATOR-07/08/10). Used by the Space's cache-regeneration pipeline (Phase 3 plan 03-05). Lazy-imports `anthropic` (Pitfall C); install via `pip install wifi-diag-narrator[llm]`.

## Citation guardrail

Every `EvidenceItem.telemetry_path` must (a) be a real `TelemetryFrame` field, (b) resolve to non-null in the actual telemetry payload (D-NARRATOR-02). Invalid citations are stripped silently (D-NARRATOR-01).

## Install

```bash
# Templated narrator only (zero network deps; agent local-only mode):
pip install wifi-diag-narrator==0.1.0

# With Anthropic LLM narrator (Space cache-regen pipeline):
pip install wifi-diag-narrator[llm]==0.1.0
```

## Public API

```python
from wifi_diag_narrator import (
    EVIDENCE_RULES,             # dict[DisconnectClass, list[str]]
    narrate_templated,          # deterministic, no network
    strip_invalid_citations,    # post-LLM guardrail
    is_valid_citation,          # single-citation check
    build_system_prompt,        # for prompt-caching workflows
)

# LLM path (requires anthropic + ANTHROPIC_API_KEY):
from wifi_diag_narrator.anthropic_narrator import narrate
```

## Versioning

Strict SemVer aligned with `wifi-diag-schema`:

- **Major** = breaking change to the narrator's public API
- **Minor** = additive (new template, new evidence rule)
- **Patch** = doc-only / wording-only

## Release

Tag a release as `vX.Y.Z`; the `release.yml` workflow runs OIDC Trusted Publishing automatically.

## License

Apache-2.0.
