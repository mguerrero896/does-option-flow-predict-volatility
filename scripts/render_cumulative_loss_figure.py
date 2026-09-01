"""Render cumulative session-loss sensitivity from a versioned public aggregate."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from figure_style import (  # noqa: E402
    ACCENT,
    INK,
    LINK,
    MONO,
    MUTED,
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
    assert_no_sealed_paths,
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
PUBLIC_SERIES = ROOT / "artifacts/rp2_v3/cumulative_loss_session_series_v1.json"
CANONICAL_INFERENCE = (
    ROOT
    / "artifacts/rp2_v3/rp2-v3-20260831-b1-spot-cutoff-remediation"
    / INFERENCE_OUTPUT
)
PUBLIC_SCHEMA = "rp2-cumulative-loss-session-series-v1.0"
PX_PER_SESSION = 4.0
Y_LIMIT = 0.31


def _read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"RP2_FIGURE_JSON_OBJECT_REQUIRED:{path.name}")
    return payload


def _contained_file(run_dir: Path, relative: str) -> Path:
    root = run_dir.resolve()
    try:
        path = (root / relative).resolve(strict=True)
    except OSError:
        raise ValueError(f"RP2_FIGURE_ARTIFACT_MISSING:{relative}") from None
    if not path.is_relative_to(root):
        raise ValueError(f"RP2_FIGURE_ARTIFACT_ESCAPE:{relative}")
    assert_no_sealed_paths([path])
    if not path.is_file():
        raise ValueError(f"RP2_FIGURE_ARTIFACT_MISSING:{relative}")
    return path


def _registered_artifact(
    run_dir: Path, manifest: dict[str, Any], step_name: str, output: str
) -> Path:
    path = _contained_file(run_dir, output)
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
        differences = np.asarray([row["delta_loss"] for row in rows], dtype=np.float64)
        component_fields = [
            "loss_without_flow" in row and "loss_with_flow" in row for row in rows
        ]
        if any(component_fields) and not all(component_fields):
            raise ValueError(f"RP2_FIGURE_LOSS_COMPONENTS_INCOMPLETE:{family}")
        values = differences
        if all(component_fields):
            without = np.asarray([row["loss_without_flow"] for row in rows], dtype=np.float64)
            with_flow = np.asarray([row["loss_with_flow"] for row in rows], dtype=np.float64)
            values = np.concatenate((without, with_flow, differences))
            if not np.allclose(differences, without - with_flow, rtol=0.0, atol=1e-12):
                raise ValueError(f"RP2_FIGURE_DELTA_MISMATCH:{family}")
        if not np.isfinite(values).all():
            raise ValueError(f"RP2_FIGURE_NONFINITE_LOSS:{family}")
        nested = role_record["nested_tests"][family]["b2_over_b1"]
        estimate = float(nested["estimate"])
        mde = float(nested["mde"])
        if not math.isfinite(mde) or mde <= 0.0:
            raise ValueError(f"RP2_FIGURE_THRESHOLD_INVALID:{family}")
        if not math.isclose(float(differences.mean()), estimate, rel_tol=0.0, abs_tol=1e-15):
            raise ValueError(f"RP2_FIGURE_AGGREGATE_MISMATCH:{family}")
        cumulative = list(itertools.accumulate(float(value) for value in differences))
        endpoint_expected = expected_sessions * estimate
        if not math.isclose(cumulative[-1], endpoint_expected, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"RP2_FIGURE_ENDPOINT_MISMATCH:{family}")

        positive = sorted((float(value) for value in differences if value > 0.0), reverse=True)
        total_rise = sum(positive)
        top_positive_share = sum(positive[:3]) / total_rise if total_rise else 0.0
        top_indices = sorted(
            range(expected_sessions),
            key=lambda index: abs(float(differences[index])),
            reverse=True,
        )[:3]
        counterfactual_differences = [
            0.0 if index in top_indices else float(value)
            for index, value in enumerate(differences)
        ]
        counterfactual = list(itertools.accumulate(counterfactual_differences))
        endpoint = cumulative[-1]
        final_bound = expected_sessions * mde
        prefix_ratios = [
            abs(value) / (mde * index) for index, value in enumerate(cumulative, start=1)
        ]
        max_prefix_index = max(range(expected_sessions), key=prefix_ratios.__getitem__)
        summary[family] = {
            "sessions": expected_sessions,
            "first_scored_session": dates[0].isoformat(),
            "last_scored_session": dates[-1].isoformat(),
            "rising_sessions": len(positive),
            "total_rise": total_rise,
            "top_three_rise_share": top_positive_share,
            "top_absolute_sessions": [
                {
                    "session_date": dates[index].isoformat(),
                    "delta_loss": float(differences[index]),
                    "index": index,
                }
                for index in top_indices
            ],
            "top_three_signed_share_of_endpoint": (
                sum(float(differences[index]) for index in top_indices) / endpoint
                if endpoint
                else 0.0
            ),
            "endpoint": endpoint,
            "aggregate_estimate": estimate,
            "endpoint_expected": endpoint_expected,
            "mde_per_session": mde,
            "full_window_bound": final_bound,
            "final_bound_ratio": abs(endpoint) / final_bound,
            "maximum_linear_prefix_ratio": prefix_ratios[max_prefix_index],
            "maximum_linear_prefix_session": dates[max_prefix_index].isoformat(),
            "counterfactual": counterfactual,
            "counterfactual_endpoint": counterfactual[-1],
        }
        curves[family] = (dates, cumulative)
    return summary, curves


def public_series_payload(
    manifest: dict[str, Any],
    inference: dict[str, Any],
    masks: dict[str, Any],
    inference_path: Path,
    canonical_inference: dict[str, Any],
) -> dict[str, Any]:
    """Strip a registered inference artifact down to publishable session aggregates."""

    estimate_differences: list[float] = []
    for role in ("D", "V"):
        if inference[role].get("evaluation_mask_sha256") != canonical_inference[role].get(
            "evaluation_mask_sha256"
        ):
            raise ValueError(f"RP2_FIGURE_CANONICAL_MASK_MISMATCH:{role}")
        if inference[role].get("model_provenance") != canonical_inference[role].get(
            "model_provenance"
        ):
            raise ValueError(f"RP2_FIGURE_CANONICAL_MODEL_PROVENANCE_MISMATCH:{role}")
        for family in PRIMARY_MODELS:
            for contrast in ("b1_over_b0", "b2_over_b1"):
                source_estimate = float(
                    inference[role]["nested_tests"][family][contrast]["estimate"]
                )
                canonical_estimate = float(
                    canonical_inference[role]["nested_tests"][family][contrast]["estimate"]
                )
                estimate_differences.append(abs(source_estimate - canonical_estimate))
    maximum_estimate_difference = max(estimate_differences)
    if maximum_estimate_difference != 0.0:
        raise ValueError(
            f"RP2_FIGURE_CANONICAL_ESTIMATE_MISMATCH:{maximum_estimate_difference}"
        )

    roles: dict[str, Any] = {}
    mean_differences: list[float] = []
    for role in ("D", "V"):
        role_analysis, role_curves = analyse_role(inference[role], masks[role])
        dates = role_curves[PRIMARY_MODELS[0]][0]
        models: dict[str, Any] = {}
        for family in PRIMARY_MODELS:
            rows = inference[role]["flow_loss_series"]["models"][family]
            deltas = [float(row["delta_loss"]) for row in rows]
            estimate = float(role_analysis[family]["aggregate_estimate"])
            mean_differences.append(abs(sum(deltas) / len(deltas) - estimate))
            models[family] = {
                "delta_loss": deltas,
                "estimate": estimate,
                "mde_per_session": float(role_analysis[family]["mde_per_session"]),
            }
        roles[role] = {
            "evaluation_mask_sha256": inference[role]["evaluation_mask_sha256"],
            "sessions": int(inference[role]["clusters"]),
            "session_dates": [value.isoformat() for value in dates],
            "models": models,
        }

    return {
        "schema_version": PUBLIC_SCHEMA,
        "source": {
            "registered_run_id": manifest["run_id"],
            "registered_code_commit": manifest["code_commit"],
            "registered_scientific_sha256": manifest["scientific_sha256"],
            "registered_inference_sha256": artifact_digest(inference_path),
            "registered_inference_content_sha256": stable_content_digest(inference_path),
            "canonical_run_id": CANONICAL_INFERENCE.parents[1].name,
            "canonical_inference_sha256": artifact_digest(CANONICAL_INFERENCE),
            "published_nested_estimates_compared": len(estimate_differences),
            "maximum_absolute_estimate_difference": maximum_estimate_difference,
            "maximum_series_mean_difference": max(mean_differences),
            "evaluation_masks_match_canonical": True,
            "model_provenance_matches_canonical": True,
        },
        "roles": roles,
    }


def analyse_public_series(
    payload: dict[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, tuple[list[date], list[float]]]],
]:
    """Validate the tracked aggregate and return the same structures as a local run."""

    if payload.get("schema_version") != PUBLIC_SCHEMA:
        raise ValueError("RP2_FIGURE_PUBLIC_SERIES_SCHEMA_INVALID")
    roles = payload.get("roles")
    if not isinstance(roles, dict) or set(roles) != {"D", "V"}:
        raise ValueError("RP2_FIGURE_PUBLIC_SERIES_ROLES_INVALID")

    analysis: dict[str, dict[str, Any]] = {}
    curves: dict[str, dict[str, tuple[list[date], list[float]]]] = {}
    for role in ("D", "V"):
        record = roles[role]
        if not isinstance(record, dict):
            raise ValueError(f"RP2_FIGURE_PUBLIC_ROLE_INVALID:{role}")
        dates = record.get("session_dates")
        models = record.get("models")
        sessions = int(record.get("sessions", 0))
        mask = record.get("evaluation_mask_sha256")
        if (
            not isinstance(dates, list)
            or len(dates) != sessions
            or not isinstance(models, dict)
            or set(models) != set(PRIMARY_MODELS)
            or not isinstance(mask, str)
            or len(mask) != 64
        ):
            raise ValueError(f"RP2_FIGURE_PUBLIC_ROLE_INVALID:{role}")
        nested: dict[str, Any] = {}
        series_models: dict[str, Any] = {}
        for family in PRIMARY_MODELS:
            model = models[family]
            if not isinstance(model, dict) or set(model) != {
                "delta_loss",
                "estimate",
                "mde_per_session",
            }:
                raise ValueError(f"RP2_FIGURE_PUBLIC_MODEL_INVALID:{role}:{family}")
            deltas = model["delta_loss"]
            if not isinstance(deltas, list) or len(deltas) != sessions:
                raise ValueError(f"RP2_FIGURE_PUBLIC_MODEL_INVALID:{role}:{family}")
            nested[family] = {
                "b2_over_b1": {
                    "estimate": model["estimate"],
                    "mde": model["mde_per_session"],
                }
            }
            series_models[family] = [
                {"session_date": session, "delta_loss": delta}
                for session, delta in zip(dates, deltas, strict=True)
            ]
        role_record = {
            "clusters": sessions,
            "evaluation_mask_sha256": mask,
            "nested_tests": nested,
            "flow_loss_series": {
                "schema_version": 1,
                "evaluation_mask_sha256": mask,
                "models": series_models,
            },
        }
        analysis[role], curves[role] = analyse_role(
            role_record, {"evaluation_mask_sha256": mask}
        )
    return analysis, curves


def _line_path(points: list[tuple[float, float]]) -> str:
    return " ".join(
        f"{'M' if index == 0 else 'L'} {x:.2f} {y:.2f}" for index, (x, y) in enumerate(points)
    )


def render(
    analysis: dict[str, Any],
    curves: dict[str, dict[str, tuple[list[date], list[float]]]],
) -> str:
    canvas = Canvas(
        1280,
        860,
        "Without three largest sessions, two endpoints reverse sign",
        "Session-level sensitivity of cumulative forecast-loss differences, with "
        "full-window bounds and three-session removal paths.",
        "cumulative-loss-difference",
    )
    header(
        canvas,
        "forecast-loss sensitivity",
        "Without three largest sessions, two endpoints reverse sign",
        "No full-window endpoint reaches 61% of its own bound",
    )
    panels = {
        "D": {"x": 20, "width": 840, "left": 92},
        "V": {"x": 888, "width": 370, "left": 930},
    }
    lane_centres = dict(zip(PRIMARY_MODELS, (230.0, 365.0, 500.0), strict=True))
    lane_half_height = 52.0

    def y_pos(value: float, centre: float) -> float:
        if abs(value) > Y_LIMIT:
            raise ValueError(f"RP2_FIGURE_VALUE_OUTSIDE_SCALE:{value}")
        return centre - value / Y_LIMIT * lane_half_height

    for role in ("D", "V"):
        panel = panels[role]
        px, left = int(panel["x"]), float(panel["left"])
        sessions = analysis[role][PRIMARY_MODELS[0]]["sessions"]
        plot_width = sessions * PX_PER_SESSION
        right = left + plot_width
        panel_slug = ROLE_LABELS[role].replace(" ", "-")
        canvas.front(
            f'<g data-panel="{panel_slug}" data-session-count="{sessions}" '
            f'data-plot-width="{plot_width:.2f}">'
            f'<text x="{px + 16}" y="128" fill="{INK}" font-family="{SANS}" '
            f'font-size="16" font-weight="600">{esc(ROLE_LABELS[role])}</text>'
            f'<text x="{px + 16}" y="150" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="12">{sessions} scored sessions · '
            f'{PX_PER_SESSION:.0f} px per session</text>'
            "</g>"
        )
        canvas.back(
            f'<rect x="{px}" y="108" width="{panel["width"]}" height="610" rx="8" '
            f'fill="none" stroke="{RULE_STRONG}" stroke-width="1"/>'
        )
        for family in PRIMARY_MODELS:
            dates, cumulative = curves[role][family]
            centre = lane_centres[family]
            summary = analysis[role][family]
            colour, dash = MODEL_STYLES[family]
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            upper = float(summary["full_window_bound"])
            canvas.back(
                f'<line x1="{left:.2f}" y1="{centre:.2f}" x2="{right:.2f}" '
                f'y2="{y_pos(upper, centre):.2f}" stroke="{RULE_STRONG}" '
                f'stroke-width="1.1" data-boundary="upper"/>'
                f'<line x1="{left:.2f}" y1="{centre:.2f}" x2="{right:.2f}" '
                f'y2="{y_pos(-upper, centre):.2f}" stroke="{RULE_STRONG}" '
                f'stroke-width="1.1" data-boundary="lower"/>'
                f'<line x1="{left:.2f}" y1="{centre:.2f}" x2="{right:.2f}" '
                f'y2="{centre:.2f}" stroke="{INK}" stroke-width="1.3"/>'
            )
            points = [(left, centre)] + [
                (left + (index + 1) * PX_PER_SESSION, y_pos(value, centre))
                for index, value in enumerate(cumulative)
            ]
            counterfactual_points = [(left, centre)] + [
                (left + (index + 1) * PX_PER_SESSION, y_pos(value, centre))
                for index, value in enumerate(summary["counterfactual"])
            ]
            canvas.front(
                f'<path d="{_line_path(counterfactual_points)}" fill="none" '
                f'stroke="{colour}" stroke-opacity="0.34" stroke-width="2" '
                f'stroke-dasharray="4 4" data-counterfactual="three-largest-removed"/>'
            )
            canvas.front(
                f'<path d="{_line_path(points)}" fill="none" stroke="{colour}" '
                f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'
                f"{dash_attr}/>"
            )
            for top in summary["top_absolute_sessions"]:
                index = int(top["index"])
                canvas.front(
                    f'<circle cx="{left + (index + 1) * PX_PER_SESSION:.2f}" '
                    f'cy="{y_pos(cumulative[index], centre):.2f}" r="3.2" fill="white" '
                    f'stroke="{colour}" stroke-width="1.5" data-largest-session="true"/>'
                )
            ratio = float(summary["final_bound_ratio"])
            endpoint = float(summary["endpoint"])
            canvas.front(
                f'<text x="{left:.2f}" y="{centre - lane_half_height - 10:.2f}" '
                f'fill="{colour}" font-family="{SANS}" font-size="12" font-weight="600">'
                f'{esc(MODEL_LABELS[family])}</text>'
                f'<text x="{right + 8:.2f}" y="{centre - 4:.2f}" fill="{colour}" '
                f'font-family="{SANS}" font-size="10">{endpoint:+.3f} · {ratio:.0%} of bound</text>'
            )
            counterfactual_endpoint = float(summary["counterfactual_endpoint"])
            if endpoint * counterfactual_endpoint < 0.0:
                canvas.front(
                    f'<text x="{right + 8:.2f}" y="{centre + 14:.2f}" fill="{ACCENT}" '
                    f'font-family="{SANS}" font-size="10" font-weight="600">without 3 '
                    f'{counterfactual_endpoint:+.3f} · sign reverses</text>'
                )

        first_dates = curves[role][PRIMARY_MODELS[0]][0]
        axis_y = lane_centres[PRIMARY_MODELS[-1]] + lane_half_height + 12
        for number in (1, (sessions + 1) // 2, sessions):
            x = left + number * PX_PER_SESSION
            tick_date = first_dates[number - 1]
            canvas.back(
                f'<line x1="{x:.2f}" y1="{axis_y:.2f}" x2="{x:.2f}" '
                f'y2="{axis_y + 5:.2f}" stroke="{RULE_STRONG}"/>'
            )
            canvas.front(
                f'<text x="{x:.2f}" y="{axis_y + 18:.2f}" fill="{SOFT}" '
                f'font-family="{MONO}" font-size="9" text-anchor="middle">'
                f'{tick_date.isoformat()}</text>'
            )

        if role == "D":
            first_centre = lane_centres[PRIMARY_MODELS[0]]
            for value, label in ((Y_LIMIT, "+0.310"), (0.0, "0.000"), (-Y_LIMIT, "-0.310")):
                zero_attr = ' data-axis-tick="zero"' if value == 0.0 else ""
                canvas.front(
                    f'<text x="{left - 8:.2f}" y="{y_pos(value, first_centre) + 4:.2f}" '
                    f'fill="{SOFT}" font-family="{MONO}" font-size="9" text-anchor="end"'
                    f'{zero_attr}>{label}</text>'
                )

        annotation_y = 618
        canvas.front(
            f'<text x="{px + 16}" y="{annotation_y}" fill="{INK}" font-family="{SANS}" '
            f'font-size="11" font-weight="600">Three largest absolute sessions '
            "removed in pale paths</text>"
        )
        if role == "D":
            for offset, family in enumerate(PRIMARY_MODELS, start=1):
                summary = analysis[role][family]
                dates_text = " · ".join(
                    item["session_date"] for item in summary["top_absolute_sessions"]
                )
                share = float(summary["top_three_signed_share_of_endpoint"])
                canvas.front(
                    f'<text x="{px + 16}" y="{annotation_y + offset * 22}" fill="{MUTED}" '
                    f'font-family="{MONO}" font-size="9">{esc(MODEL_LABELS[family])}: '
                    f'{dates_text} · {share:.0%} of endpoint</text>'
                )
        else:
            shared_dates = " · ".join(
                item["session_date"]
                for item in analysis[role][PRIMARY_MODELS[0]]["top_absolute_sessions"]
            )
            shares = " · ".join(
                f'{MODEL_LABELS[family]} '
                f'{analysis[role][family]["top_three_signed_share_of_endpoint"]:.0%}'
                for family in PRIMARY_MODELS
            )
            canvas.front(
                f'<text x="{px + 16}" y="{annotation_y + 22}" fill="{MUTED}" '
                f'font-family="{MONO}" font-size="9">{shared_dates}</text>'
                f'<text x="{px + 16}" y="{annotation_y + 44}" fill="{MUTED}" '
                f'font-family="{SANS}" font-size="10">{shares}</text>'
            )

    canvas.front(
        f'<text x="14" y="370" fill="{MUTED}" font-family="{SANS}" font-size="11" '
        f'text-anchor="middle" transform="rotate(-90 14 370)">Cumulative loss difference</text>'
        f'<line x1="32" y1="742" x2="72" y2="742" stroke="{INK}" stroke-width="2.2"/>'
        f'<text x="80" y="746" fill="{MUTED}" font-family="{SANS}" '
        f'font-size="11">observed path</text>'
        f'<line x1="200" y1="742" x2="240" y2="742" stroke="{INK}" stroke-opacity="0.34" '
        f'stroke-width="2" stroke-dasharray="4 4"/>'
        f'<text x="248" y="746" fill="{MUTED}" font-family="{SANS}" '
        f'font-size="11">three largest sessions removed</text>'
        f'<line x1="486" y1="748" x2="526" y2="736" stroke="{RULE_STRONG}" stroke-width="1.1"/>'
        f'<text x="534" y="746" fill="{MUTED}" font-family="{SANS}" '
        f'font-size="11">scaled full-window bound</text>'
    )
    footnote(
        canvas,
        786,
        "All six endpoints finish below 61% of their own full-window bound.",
    )
    footnote(
        canvas,
        812,
        "Diagonal bounds scale a full-window per-session threshold by scored sessions "
        "elapsed; they are not prefix-specific inference.",
    )
    footnote(
        canvas,
        838,
        "Pale paths set each model's three largest absolute session contributions to "
        "zero; this is a descriptive sensitivity check.",
    )
    return canvas.render() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="registered local run used only to regenerate the public aggregate",
    )
    parser.add_argument(
        "--series-source",
        type=Path,
        default=PUBLIC_SERIES,
        help="versioned aggregate used when --run-dir is absent",
    )
    parser.add_argument(
        "--series-output",
        type=Path,
        help="write the minimal public aggregate extracted from --run-dir",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    assert_no_sealed_paths([output])

    if args.run_dir is not None:
        run_dir = args.run_dir.resolve()
        assert_no_sealed_paths([run_dir])
        manifest = _read(_contained_file(run_dir, "run_manifest.json"))
        assert_manifest_identity_intact(manifest)
        inference_path = _registered_artifact(
            run_dir, manifest, "run-incremental-inference", INFERENCE_OUTPUT
        )
        inference = _read(inference_path)
        masks = _read(
            _registered_artifact(
                run_dir, manifest, "construct-common-masks", "common_masks.json"
            )
        )
        assert_no_sealed_paths([CANONICAL_INFERENCE])
        payload = public_series_payload(
            manifest,
            inference,
            masks,
            inference_path,
            _read(CANONICAL_INFERENCE),
        )
        if args.series_output is not None:
            series_output = args.series_output.resolve()
            assert_no_sealed_paths([series_output])
            series_output.parent.mkdir(parents=True, exist_ok=True)
            series_output.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
    else:
        if args.series_output is not None:
            parser.error("--series-output requires --run-dir")
        series_source = args.series_source.resolve()
        assert_no_sealed_paths([series_source])
        payload = _read(series_source)

    role_analysis, curves = analyse_public_series(payload)
    svg = render(role_analysis, curves)
    forbidden = ("B0", "B1", "B2", "QLIKE", "contrast", "cohort", "row mask", "MDE")
    if any(term.lower() in svg.lower() for term in forbidden):
        raise SystemExit("RP2_FIGURE_FORBIDDEN_JARGON")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(svg.encode("utf-8"))
    report = {
        "source": payload["source"],
        "roles": role_analysis,
        "svg_path": str(output),
        "svg_sha256": artifact_digest(output),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
