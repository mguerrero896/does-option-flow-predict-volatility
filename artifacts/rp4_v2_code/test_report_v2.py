"""Synthetic-only checks of the v2 report; never fit or open a real panel."""

import csv
import json
from argparse import Namespace
from pathlib import Path
from xml.etree import ElementTree

import pytest
from artifacts.rp4_v2_code import report_v2 as report


def window_fixture(directory: Path, version: str, window: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    families = report.FAMILIES[version]
    rows = []
    for day in ("2026-08-03", "2026-08-04"):
        row = {"session_date": day}
        for family in families:
            row.update(
                {f"loss__{family}__B0": 1.0, f"loss__{family}__B1": 1.2, f"loss__{family}__B2": 1.1}
            )
        rows.append(row)
    with (directory / "session_losses.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    contrasts = []
    for family in families:
        for label, base, larger in report.CONTRASTS:
            delta = rows[0][f"loss__{family}__{base}"] - rows[0][f"loss__{family}__{larger}"]
            contrasts.append(
                {
                    "family": family,
                    "contrast": label,
                    "estimate": delta,
                    "ci_low": delta - 0.3,
                    "ci_high": delta + 0.3,
                    "p_raw": 0.6,
                    "p_holm": 1.0,
                    "N_sessions": 2,
                    "N_origins": 4,
                    "qlike_reduction_percent": 100 * delta / rows[0][f"loss__{family}__{base}"],
                    "N_asset_sessions": 2,
                    "status": "COMPUTED",
                }
            )
    summary = {
        "status": "COMPUTED",
        "window": window,
        "result_label": "fixed label",
        "binding": {
            "specification_sha256": version,
            "panel_sha256": "panel",
            "release_sha256": "release",
            "code_sha256": {"model": "same"},
        },
        "N_sessions": 2,
        "N_origins": 4,
        "scheduled_sessions": 2,
        "first_session": rows[0]["session_date"],
        "last_session": rows[-1]["session_date"],
        "skipped_sessions": [],
        "contrasts": contrasts,
        "secondary": [],
        "robustness": [],
        "mincer_zarnowitz": {},
        "evaluation_quality_by_asset": [
            {
                "asset": "AAPL",
                "scheduled_rows": 4,
                "eligible_rows": 4,
                "invalid_target": 0,
                "incomplete_mandatory_predictors": 0,
                "failed_quality_gate": 0,
            }
        ],
        "completed_session_sha256": {r["session_date"] + ".json": "hash" for r in rows},
    }
    if version == "v2":
        summary["tail_secondary"] = [
            {
                "family": r["family"],
                "contrast": r["contrast"],
                "N_sessions": 2,
                "median_paired_contrast": r["estimate"],
                "trimmed_mean_5pct_each_tail": r["estimate"],
                "removed_each_tail": 0,
            }
            for r in contrasts
        ]
        summary["top_loss_sessions"] = []
        for family in families:
            for information_set in ("B0", "B1", "B2"):
                for rank, row in enumerate(rows, 1):
                    record = {
                        "family": family,
                        "ranked_information_set": information_set,
                        "rank": rank,
                        "session_date": row["session_date"],
                    }
                    for name in ("B0", "B1", "B2"):
                        record[f"qlike_{name}"] = row[f"loss__{family}__{name}"]
                    for label, base, expanded in report.CONTRASTS:
                        value = record[f"qlike_{base}"] - record[f"qlike_{expanded}"]
                        record[label] = value
                        record[label + "_sign"] = 1 if value > 0 else -1 if value < 0 else 0
                    summary["top_loss_sessions"].append(record)
    (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")


def test_summary_sign_and_count_are_bound_to_csv(tmp_path: Path) -> None:
    window_fixture(tmp_path, "v2", "primary")
    summary, rows = report.load_window(tmp_path, "v2", "v2", "primary", "fixed label")
    assert summary["contrasts"][0]["estimate"] < 0 and len(rows) == 2
    summary["contrasts"][0]["estimate"] = 0.2
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="ESTIMATE"):
        report.load_window(tmp_path, "v2", "v2", "primary", "fixed label")


@pytest.mark.parametrize("field", ["tail_secondary", "top_loss_sessions"])
def test_secondary_integrity_is_checked(tmp_path: Path, field: str) -> None:
    window_fixture(tmp_path, "v2", "primary")
    path = tmp_path / "summary.json"
    summary = json.loads(path.read_text())
    summary[field] = []
    path.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="SECONDARY|TOP_LOSS"):
        report.load_window(tmp_path, "v2", "v2", "primary", "fixed label")


def test_svg_has_eight_real_version_family_window_endpoints(tmp_path: Path) -> None:
    windows = {}
    for version in ("v1", "v2"):
        windows[version] = {}
        for window in ("primary", "confirmation"):
            directory = tmp_path / version / window
            window_fixture(directory, version, window)
            windows[version][window] = report.load_window(
                directory, version, version, window, "fixed label"
            )
    svg = ElementTree.fromstring(report.cumulative_figure(windows, *report.CONTRASTS[0]))
    curves = [node for node in svg.iter() if "data-endpoint" in node.attrib]
    assert len(curves) == 8
    assert {node.attrib["data-version"] for node in curves} == {"v1", "v2"}
    assert any(node.attrib["data-family"] == "log_ridge_harq" for node in curves)
    assert all(float(node.attrib["data-endpoint"]) == pytest.approx(-0.4) for node in curves)


def test_incomplete_input_never_writes_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(
        report, "load_spec", lambda *_: {"data_root": str(tmp_path), "label": "fixed label"}
    )
    args = Namespace(spec=tmp_path / "spec.json", spec_sha256="v2")
    with pytest.raises((FileNotFoundError, ValueError)):
        report.run(args)
    assert not (tmp_path / "docs/rp4/results_v2.md").exists()


def test_fit_rows_are_complete_causal_and_publish_only_selected_aggregates() -> None:
    rows = []
    for day in ("2026-08-03", "2026-08-04"):
        for family in report.FAMILIES["v2"]:
            for name in ("B0", "B1", "B2"):
                record = {
                    "session": day,
                    "model": family + "__" + name,
                    "train_rows": 1200,
                    "inner_valid_sessions": ["2026-07-31"],
                    "selected": {
                        "lambda": 1,
                        "rounds": 130,
                        "num_leaves": 15,
                        "validation_qlike": 0.12,
                    },
                }
                if family == "log_ridge_harq":
                    record.update(
                        {
                            "prediction_rows": 2,
                            "count_low": 1,
                            "count_high": 0,
                            "bounds": {"refit": {"lower": 0.01, "upper": 10}},
                            "preprocessing": {
                                "refit": {
                                    "active_columns": ["intercept", "feature:0"],
                                    "removed_columns": [
                                        {"column": "feature:1", "reason": "constant"}
                                    ],
                                }
                            },
                        }
                    )
                else:
                    record.update(
                        {
                            "refit_rounds": 130,
                            "count_log_low": 0,
                            "count_log_high": 0,
                            "count_variance_floor": 0,
                        }
                    )
                rows.append(record)
    flat = report.fit_diagnostics(rows, ["2026-08-03", "2026-08-04"], "primary")
    assert len(flat) == 12
    assert sum(r["linear_lower_touches"] or 0 for r in flat) == 6
    assert "coefficients" not in flat[0]
    rows[0]["inner_valid_sessions"] = ["2026-08-03"]
    with pytest.raises(ValueError, match="CAUSAL"):
        report.fit_diagnostics(rows, ["2026-08-03", "2026-08-04"], "primary")


def complete_fixture(tmp_path: Path, monkeypatch) -> Namespace:
    monkeypatch.setattr(report, "ROOT", tmp_path)
    source_paths = [
        "artifacts/rp4_v2_a1/specification.json",
        "artifacts/rp4_v2_a1/freeze.json",
        "docs/rp4/specification_v2.md",
        "docs/rp4/decision_130_v2.md",
        "artifacts/rp4_a1/specification.json",
        "docs/rp4/results_v1.md",
        "artifacts/rp4_v2_code/report_v2.py",
        "artifacts/rp4_code/report.py",
        "scripts/figure_style.py",
    ]
    for name in source_paths:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic source", encoding="utf-8")
    monkeypatch.setattr(report, "__file__", str(tmp_path / "artifacts/rp4_v2_code/report_v2.py"))
    v1_digest = report.sha256(tmp_path / "artifacts/rp4_a1/specification.json")
    monkeypatch.setattr(report, "V1_SHA", v1_digest)
    data = tmp_path / "private_data"
    spec = {
        "label": "fixed label",
        "assets": ["AAPL"],
        "data_root": str(data),
        "input_panels": {"combined": {"sha256": "original-panel"}},
    }
    monkeypatch.setattr(report, "load_spec", lambda *_: spec)
    materialized = data / "materialized"
    materialized.mkdir(parents=True)
    iv = {
        "asset": "AAPL",
        "session_date": "2026-08-03",
        "raw_asset_rows": 100,
        "iv_null_rows": 1,
        "iv_nonfinite_nonnull_rows": 0,
        "iv_below_003_rows": 2,
        "iv_above_3_rows": 1,
        "iv_rejected_total_rows": 4,
        "iv_rejected_percent": 4,
        "old_iv_eligible_rows": 99,
        "new_iv_eligible_rows": 96,
        "newly_rejected_within_old_iv_range": 3,
    }
    (materialized / "iv_filter_counts.csv").write_bytes(report.csv_bytes([iv]))
    manifest = {
        "spec_sha256": "v2",
        "preserved_values_exact_by_keys": True,
        "iv_inclusive_bounds": [0.03, 3.0],
        "raw_asset_rows": 100,
        "iv_rejected_total_rows": 4,
        "newly_rejected_within_old_iv_range": 3,
        "artifacts": {
            str(materialized / "panel.parquet"): "panel",
            str(materialized / "iv_filter_counts.csv"): report.sha256(
                materialized / "iv_filter_counts.csv"
            ),
        },
    }
    (materialized / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    audit = {"source_sha256": {}, "windows": {}}
    for version in ("v1", "v2"):
        for window, stage in (("primary", "b2"), ("confirmation", "b3")):
            directory = (
                tmp_path / "artifacts" / (("rp4" if version == "v1" else "rp4_v2") + "_" + stage)
            )
            window_fixture(directory, version, window)
            path = directory / "summary.json"
            summary = json.loads(path.read_text())
            summary["binding"]["specification_sha256"] = v1_digest if version == "v1" else "v2"
            summary["materialization_manifest_sha256"] = report.sha256(
                materialized / "manifest.json"
            )
            summary["quality_gate_column_present"] = False
            path.write_text(json.dumps(summary), encoding="utf-8")
            if version == "v1":
                audit["windows"][window] = {
                    "quality_flag_present": False,
                    "paired_contrast_centers": {
                        r["family"] + "__" + r["contrast"]: {
                            "median_of_paired_contrast": r["estimate"],
                            "trimmed_mean_5_percent_each_tail": r["estimate"],
                        }
                        for r in summary["contrasts"]
                    },
                }
                for source in (path, directory / "session_losses.csv"):
                    audit["source_sha256"][source.relative_to(tmp_path).as_posix()] = report.sha256(
                        source
                    )
            else:
                records = []
                for day in ("2026-08-03", "2026-08-04"):
                    for family in report.FAMILIES["v2"]:
                        for name in ("B0", "B1", "B2"):
                            record = {
                                "session": day,
                                "model": family + "__" + name,
                                "train_rows": 1200,
                                "inner_valid_sessions": ["2026-07-31"],
                                "selected": {
                                    "lambda": 1,
                                    "rounds": 130,
                                    "num_leaves": 15,
                                    "validation_qlike": 0.12,
                                },
                            }
                            if family == "log_ridge_harq":
                                record.update(
                                    {
                                        "prediction_rows": 2,
                                        "count_low": 1,
                                        "count_high": 0,
                                        "bounds": {"refit": {"lower": 0.01, "upper": 10}},
                                        "preprocessing": {
                                            "refit": {
                                                "active_columns": ["intercept"],
                                                "removed_columns": [],
                                            }
                                        },
                                    }
                                )
                            else:
                                record.update(
                                    {
                                        "refit_rounds": 130,
                                        "count_log_low": 0,
                                        "count_log_high": 0,
                                        "count_variance_floor": 0,
                                    }
                                )
                            records.append(record)
                private = data / "evaluation" / window
                private.mkdir(parents=True)
                (private / "fit_diagnostics.json").write_text(json.dumps(records), encoding="utf-8")
    path = tmp_path / "artifacts/rp4_v2_audit/audit.json"
    path.parent.mkdir()
    path.write_text(json.dumps(audit), encoding="utf-8")
    return Namespace(spec=tmp_path / "artifacts/rp4_v2_a1/specification.json", spec_sha256="v2")


def test_complete_report_writes_once_and_preserves_v1(tmp_path: Path, monkeypatch) -> None:
    args = complete_fixture(tmp_path, monkeypatch)
    frozen = tmp_path / "docs/rp4/results_v1.md"
    original = frozen.read_bytes()
    manifest = report.run(args)
    result = tmp_path / "docs/rp4/results_v2.md"
    rendered = result.read_text(encoding="utf-8")
    assert "-0.2" in rendered and "+0.1" in rendered
    assert "v1 p Holm" in rendered and "v2 p Holm" in rendered
    assert "solo los nueve" not in rendered and "Los otros siete" in rendered
    assert "columna rp4_eligible ausente" in rendered
    assert "selección adaptativa" in rendered
    assert "No se recalcula el umbral con la máscara ampliada de v2" in rendered
    assert "antes de filtrar NBBO, tamaño u horario" in rendered
    assert "no es el descarte total ni la pérdida de filas utilizables del panel" in rendered
    assert manifest["high_flow_reference"]["panel_sha256"] == "original-panel"
    assert not manifest["high_flow_reference"]["threshold_recomputed_with_v2_eligibility"]
    assert manifest["iv_count_accounting"]["total_rejected_includes_missing_and_nonfinite"]
    assert not manifest["raw_or_origin_data_read"] and manifest["models_fitted"] == 0
    assert not any("private_data" in name for name in manifest["inputs_sha256"])
    assert report.run(args) == manifest and frozen.read_bytes() == original
    result.write_text("existing unrelated result", encoding="utf-8")
    with pytest.raises(ValueError, match="IMMUTABLE_OUTPUT"):
        report.run(args)
    assert result.read_text() == "existing unrelated result"


def test_materialization_pin_drift_blocks_all_output(tmp_path: Path, monkeypatch) -> None:
    args = complete_fixture(tmp_path, monkeypatch)
    path = tmp_path / "private_data/materialized/iv_filter_counts.csv"
    path.write_text(path.read_text().replace(",100,", ",200,"), encoding="utf-8")
    with pytest.raises(ValueError, match="MATERIALIZATION_PIN"):
        report.run(args)
    assert not (tmp_path / "docs/rp4/results_v2.md").exists()


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("iv_null_rows", 0, "ROW_ACCOUNTING"),
        ("iv_nonfinite_nonnull_rows", -1, "ROW_ACCOUNTING"),
        ("old_iv_eligible_rows", 98, "ROW_ACCOUNTING"),
        ("iv_rejected_percent", 100.0 * 4 / 99, "PERCENT_DENOMINATOR"),
    ],
)
def test_iv_accounting_separates_total_incremental_and_raw_denominator(
    tmp_path: Path, monkeypatch, field: str, value: int | float, reason: str
) -> None:
    complete_fixture(tmp_path, monkeypatch)
    materialized = tmp_path / "private_data/materialized"
    manifest = report.read_json(materialized / "manifest.json")
    rows = report.read_csv(materialized / "iv_filter_counts.csv")
    report.validate_iv_counts(rows, manifest)
    rows[0][field] = value
    with pytest.raises(ValueError, match=reason):
        report.validate_iv_counts(rows, manifest)


def test_iv_counts_reject_duplicate_asset_session(tmp_path: Path, monkeypatch) -> None:
    complete_fixture(tmp_path, monkeypatch)
    materialized = tmp_path / "private_data/materialized"
    manifest = report.read_json(materialized / "manifest.json")
    rows = report.read_csv(materialized / "iv_filter_counts.csv")
    with pytest.raises(ValueError, match="DUPLICATE_SESSION_ASSET"):
        report.validate_iv_counts(rows * 2, manifest)
