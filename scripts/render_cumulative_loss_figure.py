"""Render the registered cumulative session-loss path outside the repository."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from figure_style import (  # noqa: E402
    INK,
    LINK,
    MONO,
    MUTED,
    RULE,
    RULE_STRONG,
    SANS,
    SOFT,
    Canvas,
    esc,
    footnote,
    header,
)

from mds650.rp2.ladder import PRIMARY_MODELS  # noqa: E402
from mds650.rp2.run_manifest import (  # noqa: E402
    artifact_digest,
    assert_manifest_identity_intact,
    stable_content_digest,
)

ROLE_LABELS = {"D": "model development", "V": "held-out check"}
MODEL_LABELS = {
    "gamma_glm": "Gamma GLM",
    "ridge_log": "ridge-log",
    "lightgbm_qlike": "LightGBM",
}
MODEL_STYLES = {
    "gamma_glm": (INK, ""),
    "ridge_log": (LINK, "8 5"),
    "lightgbm_qlike": (MUTED, "2 4"),
}
INFERENCE_OUTPUT = "rp2_block10_inference/inference.json"


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"RP2_FIGURE_JSON_OBJECT_REQUIRED:{path.name}")
    return payload


def _registered_artifact(
    run_dir: Path, manifest: dict[str, Any], step_name: str, output: str
) -> Path:
    path = (run_dir / output).resolve(strict=True)
    if not path.is_relative_to(run_dir):
        raise ValueError(f"RP2_FIGURE_ARTIFACT_ESCAPE:{output}")
    step = next((item for item in manifest["steps"] if item["name"] == step_name), None)
    if not isinstance(step, dict):
        raise ValueError(f"RP2_FIGURE_STEP_MISSING:{step_name}")
    if artifact_digest(path) != step.get("artifacts", {}).get(output):
        raise ValueError(f"RP2_FIGURE_ARTIFACT_HASH_MISMATCH:{output}")
    if stable_content_digest(path) != step.get("content", {}).get(output):
        raise ValueError(f"RP2_FIGURE_CONTENT_HASH_MISMATCH:{output}")
    return path


def analyse_role(
    role_record: dict[str, Any], common_mask: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, tuple[list[date], list[float]]]]:
    series = role_record.get("flow_loss_series")
    if not isinstance(series, dict) or series.get("schema_version") != 1:
        raise ValueError("RP2_FIGURE_SESSION_SERIES_MISSING")
    if series.get("evaluation_mask_sha256") != role_record.get("evaluation_mask_sha256"):
        raise ValueError("RP2_FIGURE_ROLE_MASK_MISMATCH")
    if series.get("evaluation_mask_sha256") != common_mask.get("evaluation_mask_sha256"):
        raise ValueError("RP2_FIGURE_COMMON_MASK_MISMATCH")
    models = series.get("models")
    if not isinstance(models, dict) or set(models) != set(PRIMARY_MODELS):
        raise ValueError("RP2_FIGURE_MODEL_SET_MISMATCH")

    expected_sessions = int(role_record["clusters"])
    reference_dates: list[date] | None = None
    curves: dict[str, tuple[list[date], list[float]]] = {}
    summary: dict[str, Any] = {}
    for family in PRIMARY_MODELS:
        rows = models[family]
        if not isinstance(rows, list) or len(rows) != expected_sessions:
            raise ValueError(f"RP2_FIGURE_SESSION_COUNT_MISMATCH:{family}")
        dates = [date.fromisoformat(str(row["session_date"])) for row in rows]
        if dates != sorted(set(dates)):
            raise ValueError(f"RP2_FIGURE_DATES_NOT_STRICTLY_ORDERED:{family}")
        if reference_dates is not None and dates != reference_dates:
            raise ValueError(f"RP2_FIGURE_MODEL_DATES_MISMATCH:{family}")
        reference_dates = dates
        without = np.asarray([row["loss_without_flow"] for row in rows], dtype=np.float64)
        with_flow = np.asarray([row["loss_with_flow"] for row in rows], dtype=np.float64)
        differences = np.asarray([row["delta_loss"] for row in rows], dtype=np.float64)
        if not np.isfinite(np.concatenate((without, with_flow, differences))).all():
            raise ValueError(f"RP2_FIGURE_NONFINITE_LOSS:{family}")
        if not np.allclose(differences, without - with_flow, rtol=0.0, atol=1e-12):
            raise ValueError(f"RP2_FIGURE_DELTA_MISMATCH:{family}")
        estimate = float(role_record["nested_tests"][family]["b2_over_b1"]["estimate"])
        if not math.isclose(float(differences.mean()), estimate, rel_tol=0.0, abs_tol=1e-15):
            raise ValueError(f"RP2_FIGURE_AGGREGATE_MISMATCH:{family}")
        cumulative = list(itertools.accumulate(float(value) for value in differences))
        endpoint_expected = expected_sessions * estimate
        if not math.isclose(cumulative[-1], endpoint_expected, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"RP2_FIGURE_ENDPOINT_MISMATCH:{family}")

        positive = sorted(
            (
                (float(value), session.isoformat())
                for value, session in zip(differences, dates, strict=True)
            ),
            reverse=True,
        )
        positive = [item for item in positive if item[0] > 0.0]
        total_rise = sum(value for value, _ in positive)
        top = positive[:3]
        top_share = sum(value for value, _ in top) / total_rise if total_rise else 0.0
        running = 0.0
        sessions_to_half = 0
        for index, (value, _) in enumerate(positive, start=1):
            sessions_to_half = index
            running += value
            if running >= 0.5 * total_rise:
                break
        summary[family] = {
            "sessions": expected_sessions,
            "first_scored_session": dates[0].isoformat(),
            "last_scored_session": dates[-1].isoformat(),
            "monotonic_nonincreasing": not positive,
            "rising_sessions": len(positive),
            "total_rise": total_rise,
            "top_three_rise_share": top_share,
            "top_three_explain_most": top_share > 0.5,
            "sessions_to_half_of_rise": sessions_to_half,
            "top_rising_sessions": [
                {"session_date": session, "delta_loss": value} for value, session in top
            ],
            "endpoint": cumulative[-1],
            "aggregate_estimate": estimate,
            "endpoint_expected": endpoint_expected,
        }
        curves[family] = (dates, cumulative)
    return summary, curves


def _line_path(points: list[tuple[float, float]]) -> str:
    return " ".join(
        f"{'M' if index == 0 else 'L'} {x:.2f} {y:.2f}" for index, (x, y) in enumerate(points)
    )


def _x_pos(value: date, start: date, end: date, left: int, right: int, role: str) -> float:
    if not start <= value <= end:
        raise ValueError(f"RP2_FIGURE_DATE_OUTSIDE_WINDOW:{role}:{value.isoformat()}")
    return left + (value - start).days / (end - start).days * (right - left)


def render(
    analysis: dict[str, Any],
    curves: dict[str, dict[str, tuple[list[date], list[float]]]],
    windows: dict[str, Any],
) -> str:
    canvas = Canvas(
        1280,
        748,
        "Cumulative difference in forecast loss",
        "Session-by-session cumulative loss difference for models with and without option flow.",
        "cumulative-loss-difference",
    )
    header(
        canvas,
        "RP2 · DESCRIPTIVE PATH",
        "Cumulative difference in forecast loss",
        "The same scored sessions compare forecasts without and with option flow",
    )
    panel_x = {"D": 32, "V": 656}
    panel_width, plot_top, plot_bottom = 592, 170, 610
    plot_left_offset, plot_right_offset = 50, 465
    all_values = [0.0]
    for role_curves in curves.values():
        for _, cumulative in role_curves.values():
            all_values.extend(cumulative)
    low, high = min(all_values), max(all_values)
    span = high - low or 1.0
    low -= 0.1 * span
    high += 0.1 * span

    def y_pos(value: float) -> float:
        return plot_bottom - (value - low) / (high - low) * (plot_bottom - plot_top)

    y_ticks = np.linspace(low, high, 5)
    for role in ("D", "V"):
        px = panel_x[role]
        left, right = px + plot_left_offset, px + plot_right_offset
        window = windows[role]
        start = date.fromisoformat(str(window["first_session"]))
        end = date.fromisoformat(str(window["last_session"]))
        duration = (end - start).days
        if duration <= 0:
            raise ValueError(f"RP2_FIGURE_WINDOW_INVALID:{role}")

        sessions = analysis[role][PRIMARY_MODELS[0]]["sessions"]
        canvas.front(
            f'<text x="{px + 20}" y="128" fill="{INK}" font-family="{SANS}" '
            f'font-size="16" font-weight="600">{esc(ROLE_LABELS[role])}</text>'
            f'<text x="{px + 20}" y="150" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="12">{int(window["sessions"])}-session window; '
            f"{sessions} scored dates</text>"
        )
        canvas.back(
            f'<rect x="{px}" y="108" width="{panel_width}" height="540" rx="8" '
            f'fill="none" stroke="{RULE_STRONG}" stroke-width="1"/>'
        )
        for tick in y_ticks:
            y = y_pos(float(tick))
            canvas.back(
                f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" '
                f'stroke="{RULE}" stroke-width="1"/>'
            )
            if role == "D":
                canvas.front(
                    f'<text x="{left - 8}" y="{y + 4:.2f}" fill="{SOFT}" '
                    f'font-family="{MONO}" font-size="10" text-anchor="end">{tick:+.3f}</text>'
                )
        zero = y_pos(0.0)
        canvas.back(
            f'<line x1="{left}" y1="{zero:.2f}" x2="{right}" y2="{zero:.2f}" '
            f'stroke="{INK}" stroke-width="1.3"/>'
        )
        midpoint = start + timedelta(days=duration // 2)
        for tick_date in (start, midpoint, end):
            x = _x_pos(tick_date, start, end, left, right, role)
            canvas.back(
                f'<line x1="{x:.2f}" y1="{plot_bottom}" x2="{x:.2f}" '
                f'y2="{plot_bottom + 5}" stroke="{RULE_STRONG}"/>'
            )
            canvas.front(
                f'<text x="{x:.2f}" y="{plot_bottom + 20}" fill="{SOFT}" '
                f'font-family="{MONO}" font-size="10" text-anchor="middle">'
                f"{tick_date.strftime('%b %Y')}</text>"
            )

        endpoints: list[tuple[float, str, str]] = []
        for family in PRIMARY_MODELS:
            dates, cumulative = curves[role][family]
            points = [
                (_x_pos(session, start, end, left, right, role), y_pos(value))
                for session, value in zip(dates, cumulative, strict=True)
            ]
            colour, dash = MODEL_STYLES[family]
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            canvas.front(
                f'<path d="{_line_path(points)}" fill="none" stroke="{colour}" '
                f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'
                f"{dash_attr}/>"
            )
            endpoints.append((points[-1][1], family, colour))

        placed: list[tuple[float, str, str, float]] = []
        last_y = plot_top - 18.0
        for actual_y, family, colour in sorted(endpoints):
            label_y = max(actual_y, last_y + 18.0)
            placed.append((actual_y, family, colour, label_y))
            last_y = label_y
        overflow = max((label_y for *_, label_y in placed), default=plot_bottom) - plot_bottom
        if overflow > 0:
            placed = [
                (actual, family, colour, label - overflow)
                for actual, family, colour, label in placed
            ]
        for actual_y, family, colour, label_y in placed:
            canvas.front(
                f'<line x1="{right}" y1="{actual_y:.2f}" x2="{right + 8}" '
                f'y2="{label_y:.2f}" stroke="{colour}" stroke-width="1"/>'
                f'<text x="{right + 12}" y="{label_y + 4:.2f}" fill="{colour}" '
                f'font-family="{SANS}" font-size="11">{esc(MODEL_LABELS[family])} '
                f"{analysis[role][family]['endpoint']:+.3f}</text>"
            )

    canvas.front(
        f'<text x="18" y="420" fill="{MUTED}" font-family="{SANS}" font-size="11" '
        f'text-anchor="middle" transform="rotate(-90 18 420)">Cumulative loss difference</text>'
    )
    footnote(
        canvas,
        686,
        "Above zero, option flow had helped up to that date; below zero, it had not.",
    )
    footnote(
        canvas,
        716,
        "Descriptive path only; it is not a statistical test or a state-promotion decision.",
    )
    return canvas.render() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise SystemExit("RP2_FIGURE_OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")

    manifest = _read(run_dir / "run_manifest.json")
    assert_manifest_identity_intact(manifest)
    inference_path = _registered_artifact(
        run_dir, manifest, "run-incremental-inference", INFERENCE_OUTPUT
    )
    inference = _read(inference_path)
    masks = _read(
        _registered_artifact(run_dir, manifest, "construct-common-masks", "common_masks.json")
    )
    inputs = _read(
        _registered_artifact(
            run_dir, manifest, "validate-input-manifests", "input_manifest.json"
        )
    )
    windows = inputs.get("study_window_enforced")
    if not isinstance(windows, dict):
        raise SystemExit("RP2_FIGURE_STUDY_WINDOW_MISSING")

    analysis: dict[str, Any] = {
        "run_id": manifest["run_id"],
        "code_commit": manifest["code_commit"],
        "scientific_sha256": manifest["scientific_sha256"],
        "roles": {},
    }
    curves: dict[str, dict[str, tuple[list[date], list[float]]]] = {}
    for role in ("D", "V"):
        role_analysis, role_curves = analyse_role(inference[role], masks[role])
        analysis["roles"][role] = role_analysis
        curves[role] = role_curves
    svg = render(analysis["roles"], curves, windows)
    forbidden = ("B0", "B1", "B2", "QLIKE", "contrast", "cohort", "row mask", "MDE")
    if any(term.lower() in svg.lower() for term in forbidden):
        raise SystemExit("RP2_FIGURE_FORBIDDEN_JARGON")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    analysis["svg_path"] = str(output)
    analysis["svg_sha256"] = artifact_digest(output)
    print(json.dumps(analysis, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
