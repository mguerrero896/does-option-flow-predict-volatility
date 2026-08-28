"""Block 7 fits two treatment batteries, and the artifact has to say how they relate.

`CORE_TREATMENTS` and `tuple(B2_FEATURES)` overlap without nesting: each names channels
the other does not, and in validation they disagree (core_V does not reject, full_V does).
Which one is the primary joint test lives only in a source comment, so a reader of
`dml.json` can quote `full_V` as "B2 contributes in validation" with nothing in the
artifact to contradict them. The declaration below is what the artifact must carry.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "rp2_block7_dml.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rp2_block7_dml", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["rp2_block7_dml"] = module
    spec.loader.exec_module(module)
    return module


def test_the_declaration_names_the_primary_battery_and_its_keys() -> None:
    declaration = _load().describe_treatment_batteries()
    assert declaration["primary"] == "core"
    assert declaration["primary_keys"] == ["core_D", "core_V"]
    assert declaration["secondary"] == "full"
    assert declaration["secondary_keys"] == ["full_D", "full_V"]


def test_the_declaration_states_that_the_two_batteries_are_not_nested() -> None:
    declaration = _load().describe_treatment_batteries()
    assert declaration["nested"] is False
    assert declaration["relation"] == "OVERLAPPING_NOT_NESTED"
    assert declaration["only_in_primary"] == [
        "b2_5m_gamma_flow",
        "b2_5m_otm_premium_share",
    ]
    assert declaration["only_in_secondary"] == [
        "b2_5m_mean_provider_latency_s",
        "b2_5m_multileg_size_share",
        "b2_5m_vega_flow_short_dte",
        "b2_5m_zero_dte_premium_share",
    ]


def test_the_declaration_says_the_secondary_battery_is_not_the_whole_of_b2() -> None:
    """'full' resolves to B2_CORE, twelve of the fifty-six channels B2_RICH declares."""

    declaration = _load().describe_treatment_batteries()
    assert declaration["secondary_registry_set"] == "B2_CORE"
    assert declaration["secondary_is_complete_b2"] is False
    assert declaration["b2_rich_count"] > declaration["secondary_count"]


def test_the_document_carries_the_declaration() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"treatment_batteries": describe_treatment_batteries(),' in source
