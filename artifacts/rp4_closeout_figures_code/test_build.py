"""Synthetic tests; no model fit, target read or bootstrap."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
from artifacts.rp4_closeout_figures_code import build as b


def test_interval_rescales_only_saved_difference() -> None:
    assert b.percent_interval(0.02, -0.01, 0.04, 0.2) == (10.0, -5.0, 20.0)


@pytest.mark.parametrize("base", [0, -1, math.nan, math.inf, None])
def test_invalid_denominator_is_never_zero_success(base: Any) -> None:
    with pytest.raises(ValueError):
        b.percent_interval(0.02, -0.01, 0.04, base)


def test_huge_adverse_values_are_not_clipped() -> None:
    point, low, high = b.percent_interval(-243.7, -731.1, 0.002, 0.1455)
    lo, hi = b.extent([point, low, high])
    assert lo < low < point < -100 < 0 < high < hi


def test_reversed_interval_rejected() -> None:
    with pytest.raises(ValueError, match="INTERVAL"):
        b.percent_interval(0, 1, -1, 0.2)


def test_cumulative_preserves_every_session_and_sign() -> None:
    rows = [
        {"session_date": "2026-08-03", "loss__test__B0": "0.2", "loss__test__B1": "0.1"},
        {"session_date": "2026-08-04", "loss__test__B0": "0.1", "loss__test__B1": "0.4"},
    ]
    dates, values = b.cumulative_data(rows, "test", "B0", "B1")
    assert len(dates) == len(values) == 2
    assert values == pytest.approx([0.1, -0.2])
    with pytest.raises(ValueError, match="DATE_ORDER"):
        b.cumulative_data(rows[::-1], "test", "B0", "B1")


def test_nonfinite_curve_is_not_silently_dropped() -> None:
    with pytest.raises(ValueError, match="FINITE"):
        b.cumulative_data(
            [{"session_date": "2026-08-03", "loss__test__B0": "nan", "loss__test__B1": "0.1"}],
            "test",
            "B0",
            "B1",
        )


@pytest.mark.parametrize("word", b.EXCLUDED_WORDS)
def test_public_identity_guard(word: str) -> None:
    with pytest.raises(ValueError, match="IDENTITY"):
        b.public_guard(("safe " + word.upper()).encode())


def test_missing_or_drifted_pin_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(b, "ROOT", tmp_path)
    path = tmp_path / "saved.json"
    path.write_text("{}")
    valid = {"inputs_sha256": {"saved.json": b.digest(path)}}
    assert b.pinned_input(path, valid) == b.digest(path)
    with pytest.raises(ValueError, match="FROZEN_INPUT_HASH"):
        b.pinned_input(path, {"input_sha256": {"saved.json": "0" * 64}})


def test_write_once_never_replaces_prior_file(tmp_path: Path) -> None:
    path = tmp_path / "plot.svg"
    b.write_new(path, b"one")
    b.write_new(path, b"one")
    with pytest.raises(FileExistsError):
        b.write_new(path, b"two")
    assert path.read_bytes() == b"one"


def fake_comparison() -> b.Rows:
    rows = []
    for version, horizon in b.SERIES:
        for window in b.WINDOWS:
            for group in ("linear", "tree"):
                for contrast, _, _ in b.CONTRASTS:
                    adverse = version == "v1" and group == "linear" and contrast == "B2_over_B1"
                    rows.append(
                        {
                            "version": version,
                            "horizon_minutes": horizon,
                            "window": window,
                            "family_group": group,
                            "contrast": contrast,
                            "percent_reduction": -167448.32 if adverse else 1.2,
                            "ci_low_rescaled_percent": -502323.64 if adverse else -0.4,
                            "ci_high_rescaled_percent": 2.4,
                            "N_sessions": 419,
                            "N_origins": 160832,
                        }
                    )
    return rows


def test_comparison_40_panels_and_visible_adverse_extent() -> None:
    svg = b.comparison_svg(fake_comparison())
    root = ET.fromstring(svg)
    assert root.attrib["width"] == "2100"
    text = svg.decode()
    assert text.count("N = 419 sesiones") == 40
    assert "−1.6745e+05 %" in text
    assert "NO es un IC bootstrap del cociente" in text
    b.public_guard(svg)


def test_duplicate_comparison_panel_is_rejected() -> None:
    rows = fake_comparison()
    rows.append(rows[0])
    with pytest.raises(ValueError, match="FACET_IDENTITY"):
        b.comparison_svg(rows)


def test_cumulative_labels_all_context_inside_svg() -> None:
    results: b.Results = {}
    for horizon in (15, 5):
        for window in b.WINDOWS:
            rows: b.Rows = []
            days = (
                ("2025-04-07", "2026-06-17")
                if window == "primary"
                else ("2026-08-03", "2026-09-04")
            )
            for day in days:
                row: dict[str, Any] = {"session_date": day}
                for family in b.FAMILIES:
                    row[f"loss__{family}__B0"] = 0.2
                    row[f"loss__{family}__B1"] = 0.1
                rows.append(row)
            results["v4", horizon, window] = ({"N_sessions": 2}, rows)
    svg, panels = b.cumulative_svg(results, "B1_over_B0", "B0", "B1")
    ET.fromstring(svg)
    text = svg.decode()
    for day, _, _ in b.EVENTS:
        assert day in text
    assert "noticia o earnings NO demostrados" in text
    assert "Ejes Y independientes" in text
    assert len(panels) == 8
    assert all(row["final_cumulative_delta"] == pytest.approx(0.2) for row in panels)
    b.public_guard(svg)
