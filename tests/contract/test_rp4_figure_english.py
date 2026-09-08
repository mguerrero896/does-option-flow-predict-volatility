"""Current English presentation figures retain the exact saved scientific geometry."""

import json

import pytest
from docs.figures.rp4 import reproduce_english as figures


def test_english_figures_reproduce_all_saved_points_intervals_and_numbers() -> None:
    expected = json.loads((figures.HERE / "translation_receipt.json").read_text("utf-8"))
    rendered, checks = figures.render_svg_set()
    assert len(rendered) == 6
    assert checks == expected["svg_invariants"]
    assert sum(row["xml_elements_with_identical_attributes"] for row in checks.values()) == 1395
    assert (
        sum(row["numeric_tokens_preserved_in_order_per_text_node"] for row in checks.values())
        == 1033
    )
    for name, data in rendered.items():
        assert data == (figures.HERE / name).read_bytes(), name
        assert figures.sha(data) == expected["output_sha256"][f"docs/figures/rp4/{name}"]
    for relative, expected_hash in expected["output_sha256"].items():
        assert figures.sha((figures.ROOT / relative).read_bytes()) == expected_hash, relative


def test_translation_rejects_a_changed_numeric_label() -> None:
    source = b'<svg xmlns="http://www.w3.org/2000/svg"><text>N = 419</text></svg>'
    with pytest.raises(AssertionError, match="Numeric label drift"):
        figures.english_svg(source, {"exact": {"N = 419": "N = 420"}, "phrases": []})
