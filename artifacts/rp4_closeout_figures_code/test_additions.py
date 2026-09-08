"""Display-only regression tests on synthetic results."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from typing import Any

import pytest
from artifacts.rp4_closeout_figures_code import additions as a
from artifacts.rp4_closeout_figures_code import build as b
from artifacts.rp4_closeout_figures_code.test_build import fake_comparison


def test_month_ticks_are_first_observed_sessions() -> None:
    days = list(map(date.fromisoformat, ["2026-08-03", "2026-08-04", "2026-09-01", "2026-09-02"]))
    ticks = a.real_session_ticks(days, "month")
    assert ticks == [days[0], days[2]]
    assert set(ticks).issubset(days)


def test_quarter_ticks_never_invent_calendar_holiday() -> None:
    days = list(map(date.fromisoformat, ["2024-10-28", "2024-12-31", "2025-01-02", "2025-04-01"]))
    assert a.real_session_ticks(days, "quarter") == [days[0], days[2], days[3]]
    with pytest.raises(ValueError):
        a.real_session_ticks(days[::-1], "quarter")


@pytest.mark.parametrize(
    "point,low,high,flags",
    [
        (1, -4, 5, (False, False, True, True)),
        (-8, -24, 1, (True, False, True, False)),
        (7, 4, 10, (False, True, True, True)),
        (3, -3, 3, (False, False, False, False)),
    ],
)
def test_all_out_of_scale_endpoints_are_flagged(
    point: float, low: float, high: float, flags: tuple[bool, ...]
) -> None:
    result = a.clipping(point, low, high)
    assert (
        tuple(
            result[key]
            for key in (
                "point_clipped_low",
                "point_clipped_high",
                "ci_low_clipped",
                "ci_high_clipped",
            )
        )
        == flags
    )


def test_thesis_uses_only_primary_and_marks_all_clips() -> None:
    rows = fake_comparison()
    for row in rows:
        row["family"] = (
            "log_ols_harq"
            if row["version"] == "v1" and row["family_group"] == "linear"
            else "log_ridge_harq"
        )
        if row["version"] == "v2" and row["family_group"] == "tree":
            row["ci_high_rescaled_percent"] = 5.5
    svg, census = a.thesis_svg(rows)
    ET.fromstring(svg)
    assert len(census) == 20
    assert all(row["window"] == "primary" for row in census)
    assert b"data-out-of-scale" in svg
    assert "−167448.32 %" in svg.decode()
    assert "IC +5.5" in svg.decode()
    expected_arrows = sum(
        row["point_clipped_low"]
        + row["point_clipped_high"]
        + row["ci_low_clipped"]
        + row["ci_high_clipped"]
        for row in census
    )
    assert svg.decode().count("data-out-of-scale=") == expected_arrows
    b.public_guard(svg)


def test_revised_curve_coordinates_are_identical_and_ticks_real() -> None:
    results: b.Results = {}
    for horizon in (15, 5):
        for window in b.WINDOWS:
            days = (
                ("2025-04-07", "2026-01-26", "2026-06-17")
                if window == "primary"
                else ("2026-08-03", "2026-09-01", "2026-09-04")
            )
            rows: b.Rows = []
            for day in days:
                row: dict[str, Any] = {"session_date": day}
                for family in b.FAMILIES:
                    row[f"loss__{family}__B0"] = 0.2
                    row[f"loss__{family}__B1"] = 0.1
                rows.append(row)
            results["v4", horizon, window] = ({"N_sessions": 3}, rows)
    old, _ = b.cumulative_svg(results, "B1_over_B0", "B0", "B1")
    new, panels = a.revised_curve(results, "B1_over_B0", "B0", "B1")
    old_points = [x.attrib["points"] for x in ET.fromstring(old) if x.tag.endswith("polyline")]
    new_points = [x.attrib["points"] for x in ET.fromstring(new) if x.tag.endswith("polyline")]
    assert old_points == new_points
    assert "2026-01-26" in new.decode() and "OTA2026-2" in new.decode()
    assert "Causa no identificada" in new.decode()
    tick_labels = [
        x
        for x in ET.fromstring(new)
        if x.tag.rsplit("}", 1)[-1] == "text" and float(x.attrib["y"]) in (607.0, 1072.0)
    ]
    assert all(
        x.attrib["text-anchor"] == "end"
        for x in tick_labels
        if x.text in ("2025-04-07", "2026-08-03")
    )
    for panel in panels:
        valid_days = {
            row["session_date"]
            for row in results["v4", panel["horizon_minutes"], panel["window"]][1]
        }
        assert set(panel["ticks"]).issubset(valid_days)
    b.public_guard(new)
