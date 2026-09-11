"""Public diagnostic graphics must reproduce from the saved aggregate evidence."""

from scripts.render_reader_diagnostics import OUT, assets, comparisons, scatter


def test_reader_diagnostics_match_sources():
    for name, render in (
        ("effect_intervals.svg", comparisons),
        ("asset_heatmap.svg", assets),
        ("paired_session_losses.svg", scatter),
    ):
        assert (OUT / name).read_bytes() == render()
    assert scatter().count(b"<circle ") == 838
