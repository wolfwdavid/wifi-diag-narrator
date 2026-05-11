"""Regression tests for the wifi_diag_narrator top-level public API.

Phase 6 plan 06-03 closes the audit INFO gap by re-exporting the four
public-API names from ``wifi_diag_narrator/__init__.py``. This test
pins that contract so a future refactor cannot silently drop a name
from the package surface.

Also guards Pitfall C: importing ``narrate`` from the top-level
package MUST NOT eagerly import ``anthropic`` (lazy import lives
inside ``narrate()`` itself).
"""
from __future__ import annotations

import subprocess
import sys

import wifi_diag_narrator


def test_public_api_re_exports() -> None:
    """The four documented public-API names are importable from the
    top-level package and present in ``__all__``."""
    # 1. Names import directly from the top-level package.
    from wifi_diag_narrator import (
        EVIDENCE_RULES,
        narrate,
        narrate_templated,
        strip_invalid_citations,
    )

    # 2. Right kind of object.
    assert isinstance(EVIDENCE_RULES, dict), (
        f"EVIDENCE_RULES expected dict, got {type(EVIDENCE_RULES)}"
    )
    assert callable(narrate), "narrate must be callable"
    assert callable(narrate_templated), "narrate_templated must be callable"
    assert callable(strip_invalid_citations), (
        "strip_invalid_citations must be callable"
    )

    # 3. Names listed in __all__ (so `from wifi_diag_narrator import *`
    #    and ``help(wifi_diag_narrator)`` discover them).
    for name in (
        "EVIDENCE_RULES",
        "narrate",
        "narrate_templated",
        "strip_invalid_citations",
    ):
        assert name in wifi_diag_narrator.__all__, (
            f"{name!r} missing from wifi_diag_narrator.__all__: "
            f"{wifi_diag_narrator.__all__!r}"
        )


def test_anthropic_not_eagerly_imported() -> None:
    """Pitfall C: importing ``narrate`` from the top-level package
    must NOT trigger an ``anthropic`` package import. The anthropic
    SDK should only be loaded when ``narrate()`` is actually called.

    This is asserted in a fresh subprocess interpreter to avoid
    test-order pollution — a sibling test in this same pytest session
    may have already pulled anthropic into ``sys.modules`` by mocking
    ``_get_client`` and exercising paths that do touch the real SDK.
    A subprocess gives a clean ``sys.modules`` to inspect.
    """
    code = (
        "import sys; "
        "from wifi_diag_narrator import narrate; "
        "assert 'anthropic' not in sys.modules, "
        "    'Pitfall C regression: importing wifi_diag_narrator at module "
        "load eagerly imported the anthropic SDK. The narrate() function "
        "must keep its import inside the function body.'; "
        "print('lazy-import ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Pitfall C subprocess assertion failed:\n"
        f"  stdout: {result.stdout!r}\n"
        f"  stderr: {result.stderr!r}"
    )
    assert "lazy-import ok" in result.stdout
