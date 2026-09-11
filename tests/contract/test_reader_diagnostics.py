"""Public diagnostic graphics must reproduce from the saved aggregate evidence."""

from docs.figures.public_refresh.render_reader_diagnostics import (
    OUT,
    assets,
    comparisons,
    scatter,
    timing_points,
    timing_sensitivity,
)


def test_reader_diagnostics_match_sources():
    for name, render in (
        ("effect_intervals.svg", comparisons),
        ("asset_heatmap.svg", assets),
        ("paired_session_losses.svg", scatter),
        ("timing_sensitivity.svg", timing_sensitivity),
    ):
        assert (OUT / name).read_bytes() == render()
    assert scatter().count(b"<circle ") == 838
    points = timing_points()
    assert [round(v, 3) for _, v, _ in points["B2_over_B1"]] == [1.447, 0.623, 0.194]
    assert [round(v, 3) for _, v, _ in points["B1_over_B0"]] == [0.841, 0.880, 0.912]
    assert [p for _, _, p in points["B2_over_B1"]] == [0.0001, 0.0032, 0.1948]
