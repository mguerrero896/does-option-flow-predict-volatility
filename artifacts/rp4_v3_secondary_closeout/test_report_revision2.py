"""Synthetic closeout gates: no production summaries, targets, fits or inference."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from artifacts.rp4_v3_secondary_closeout import report_revision2 as report

BLOCK = (
    "| Ventana | Familia | Contraste | Delta | IC95% | Reducción % | "
    "p unilateral nominal | Decisión | N sesiones/orígenes |\n"
    "|---|---|---|---:|---|---:|---:|---|---|\n"
    "| Primaria | Ridge | B1/B0 | +0.0025468959 | [0.0005570053, 0.0055407196] | "
    "+1.7289745 | 0.0439 | H1 rechazada | 419/160832 |\n"
    "| Primaria | Ridge | B2/B1 | +0.0008023897 | [-0.0001534347, 0.0017735437] | "
    "+0.5542902 | 0.0525 | H2 no rechazada | 419/160832 |\n"
    "| Primaria | LightGBM | B1/B0 | +0.0031224859 | [0.0010149407, 0.0054860165] | "
    "+2.0911798 | 0.0053 | H1 rechazada | 419/160832 |\n"
    "| Primaria | LightGBM | B2/B1 | -0.0002326470 | [-0.0016475987, 0.0008319668] | "
    "-0.1591353 | 0.6631 | H2 no rechazada | 419/160832 |\n"
    "| Confirmación | Ridge | B1/B0 | +0.0009113921 | [-0.0028274372, 0.0039476574] | "
    "+0.5010983 | 0.3238 | H1 no rechazada | 25/9750 |\n"
    "| Confirmación | Ridge | B2/B1 | +0.0033669574 | [-0.0007443023, 0.0102227627] | "
    "+1.8605313 | 0.1612 | H2 no abierta; p sólo diagnóstico | 25/9750 |\n"
    "| Confirmación | LightGBM | B1/B0 | +0.0029141581 | [-0.0016852924, 0.0074221881] | "
    "+1.6658018 | 0.1104 | H1 no rechazada | 25/9750 |\n"
    "| Confirmación | LightGBM | B2/B1 | -0.0041525214 | [-0.0103787975, 0.0000249181] | "
    "-2.4138902 | 0.9266 | H2 no abierta; p sólo diagnóstico | 25/9750 |\n"
).encode()


def original_summaries() -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {window: {"contrasts": []} for window in report.WINDOWS}
    for line in BLOCK.decode().splitlines()[2:]:
        fields = [f.strip() for f in line.strip("|").split("|")]
        low, high = map(float, fields[4].strip("[]").split(", "))
        n_sessions, n_origins = map(int, fields[8].split("/"))
        window = next(k for k, v in report.WINDOWS.items() if v == fields[0])
        summaries[window]["contrasts"].append(
            {
                "family": report.FAMILIES[0] if fields[1] == "Ridge" else report.FAMILIES[1],
                "contrast": fields[2].replace("/", "_over_"),
                "estimate": float(fields[3]),
                "ci_low": low,
                "ci_high": high,
                "qlike_reduction_percent": float(fields[5]),
                "p_raw": float(fields[6]),
                "N_sessions": n_sessions,
                "N_origins": n_origins,
                "endpoint": "qlike_mean",
                "statistic": "mean",
                "inference_role": "PRIMARY",
            }
        )
    return summaries


def solver(*, new: bool) -> dict[str, Any]:
    result = {"converged": True, "gradient_inf_norm_objective_over_n": 1e-10 if new else 2e-7}
    if new:
        result.update(
            original_gradient_certificate_applicable=True,
            stable_gradient_inf_norm=1e-10,
            objective_total_divided_by_n=0.5,
            objective_initial_divided_by_n=0.7,
            literal_original_objective_abs_difference=1e-16,
            literal_original_gradient_max_abs_difference=1e-16,
        )
    return result


def fixture_window(window: str = "primary") -> dict[str, Any]:
    sessions = ["2026-01-02", "2026-01-05"]
    fits, components, sources = [], [], []
    for i, session in enumerate(sessions):
        for model in report.MODELS:
            old = i == 0
            row = {
                "session": session,
                "model": model,
                "status": "COMPUTED",
                "provenance": report.PROVENANCES[0 if old else 1],
                "fit": {
                    "solver_refit": solver(new=not old),
                    "candidates": [{"solver": solver(new=not old)} for _ in range(5)],
                },
                "failure": None,
            }
            fits.append(row)
            components.append(
                {k: row[k] for k in ("session", "model", "status", "provenance")}
                | {
                    "original_component_sha256": "a" * 64 if old else None,
                    "component_sha256": "b" * 64,
                    "receipt_sha256": "c" * 64,
                }
            )
            if old:
                sources.append({"session": session, "model": model, "component_sha256": "a" * 64})
    contrasts = []
    for family in report.FAMILIES:
        for contrast in ("B1_over_B0", "B2_over_B1"):
            second = contrast == "B2_over_B1"
            contrasts.append(
                {
                    "family": family,
                    "contrast": contrast,
                    "endpoint": "jump_auc",
                    "inference_role": "SECONDARY",
                    "status": "COMPUTED",
                    "estimate": -0.01,
                    "ci_low": -0.03,
                    "ci_high": 0.01,
                    "p_raw": 0.8,
                    "alternative": "greater",
                    "hypothesis_status": "NOT_TESTED" if second else "NOT_REJECTED",
                    "rejected": False,
                    "p_for_decision": None if second else 0.8,
                    "N_sessions": 2,
                    "N_origins": 20,
                }
            )
    jump = {
        "endpoint": "jump_auc",
        "inference_role": "SECONDARY",
        "status": "COMPUTED",
        "N_sessions": 2,
        "N_origins": 20,
        "excluded_sessions": [],
        "positive_labels": 8,
        "negative_labels": 12,
        "families": [
            {
                "family": family,
                "N_sessions": 2,
                "N_origins": 20,
                "invalid_class_resamples": 0,
                "auc": {
                    name: {"estimate": 0.55, "ci_low": 0.51, "ci_high": 0.6, "status": "COMPUTED"}
                    for name in report.SETS
                },
            }
            for family in report.FAMILIES
        ],
        "contrasts": contrasts,
        "sequence": {"scope": "SECONDARY_ENDPOINT_JOINT", "contrasts": contrasts},
    }
    gradients = []
    for provenance in report.PROVENANCES:
        item: dict[str, Any] = {"provenance": provenance}
        for row in report.certificate_counts(fits):
            if row["provenance"] == provenance:
                phase = row["phase"]
                item.update(
                    {
                        f"{phase}_gradients_available": row["gradients_available"],
                        f"{phase}_gradients_missing_or_single_class": row["gradients_unavailable"],
                        f"{phase}_gradients_above_1e_minus8": row["gradients_above_tolerance"],
                        f"{phase}_gradient_max": row["gradient_max"],
                    }
                )
        gradients.append(item)
    summary = {
        "status": "COMPLETE_SECONDARY_ATTEMPTS",
        "binding": {"release_sha256": "d" * 64, "window": window, "endpoint": "jump"},
        "primary_changed": False,
        "quantile_changed": False,
        "mz_changed": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
        "scheduled_sessions": 2,
        "session_sha256": {s + ".json": "e" * 64 for s in sessions},
        "component_counts": [
            {"provenance": p, "status": "COMPUTED", "N": 6} for p in report.PROVENANCES
        ],
        "resources": {
            "threads_total_max": 2,
            "priority": "16384",
            "process_id": 1,
            "threadpools": [{"num_threads": 2}],
            "arrow_cpu_threads": 2,
            "arrow_io_threads": 1,
            "parquet_use_threads": False,
        },
        "jump_secondary": jump,
        "gradient_diagnostics": gradients,
    }
    plan = {
        "window": window,
        "N_sessions": 2,
        "sessions": [{"session": s, "N_jump_origins": 10} for s in sessions],
        "components": sources,
        "reusable_components": 6,
        "missing_components": 6,
    }
    receipt = {
        "exit_code": 0,
        "elapsed_seconds": 1.5,
        "started_at_utc": "2026-09-07T19:00:00+00:00",
        "completed_at_utc": "2026-09-07T19:00:01.5+00:00",
    }
    return {
        "summary": summary,
        "fits": fits,
        "components": components,
        "plan": plan,
        "certificates": report.certificate_counts(fits),
        "receipt": receipt,
    }


def fixture_evidence() -> dict[str, Any]:
    mz_row = {
        "raw_qlike_recomputed": 0.1,
        "mz_qlike_recomputed": 1000.0,
        "N_origins": 20,
        "strictly_negative_affine": 1,
        "floor_hits": 1,
        "floor_loss_share_percent": 99.99,
        "formula_stored_max_abs_difference": 0.0,
    }
    return {
        "primary_block": BLOCK,
        "release_sha256": "d" * 64,
        "windows": {w: fixture_window(w) for w in report.WINDOWS},
        "mz_primary": {"results": {name: mz_row for name in report.SETS}},
        "mz_confirmation": {"results": {name: mz_row for name in report.SETS}},
    }


def validate(bundle: dict[str, Any]) -> Any:
    return report.validate_window(
        bundle["summary"], bundle["fits"], bundle["components"], bundle["plan"], "d" * 64
    )


@pytest.mark.parametrize("ending", [b"\n", b"\r\n"])
def test_primary_eight_rows_preserved_byte_for_byte(ending: bytes) -> None:
    evidence = fixture_evidence()
    evidence["primary_block"] = BLOCK.replace(b"\n", ending)
    rendered = report.render(evidence)
    assert report.primary_block(rendered) == evidence["primary_block"]
    report.verify_primary_table(evidence["primary_block"], original_summaries())


def test_original_summary_value_drift_rejected() -> None:
    summaries = original_summaries()
    summaries["primary"]["contrasts"][0]["estimate"] += 0.01
    with pytest.raises(ValueError, match="PRIMARY_DISPLAY_VALUE_DRIFT"):
        report.verify_primary_table(BLOCK, summaries)


def test_primary_row_loss_rejected() -> None:
    with pytest.raises(ValueError, match="EIGHT_ROWS"):
        report.primary_block(b"\n".join(BLOCK.splitlines()[:-1]))


def test_frozen_hash_drift_rejected(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    path.write_text('{"one":1}', encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert report.verified(path, digest, {}) == {"one": 1}
    path.write_text('{"one":2}', encoding="utf-8")
    with pytest.raises(ValueError, match="HASH_DRIFT"):
        report.verified(path, digest, {})


def test_incomplete_confirmation_rejected_before_auc_read(tmp_path: Path, monkeypatch: Any) -> None:
    private = tmp_path / "private"
    hashes = {}
    for window in report.WINDOWS:
        path = private / "evaluation" / window / "receipt.json"
        path.parent.mkdir(parents=True)
        payload = {
            "status": "COMPLETE" if window == "primary" else "FAILED_ATTEMPT_PRESERVED",
            "exit_code": 0 if window == "primary" else 1,
            "window": window,
            "release_sha256": "d" * 64,
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        hashes[window] = hashlib.sha256(path.read_bytes()).hexdigest()
    opened = []
    original_read = report.read_json

    def tracking(path: Path) -> Any:
        opened.append(path.name)
        return original_read(path)

    monkeypatch.setattr(report, "read_json", tracking)
    with pytest.raises(ValueError, match="WINDOW_NOT_CLOSED:confirmation"):
        report.load_evidence(tmp_path, private, "d" * 64, hashes)
    assert opened == ["receipt.json", "receipt.json"]
    assert not (tmp_path / report.REPORT).exists()


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), -1, 1.5, True, "0"])
def test_unavailable_n_never_zero(value: Any) -> None:
    assert report.count(value) == "NO VERIFICABLE"


def test_verified_zero_can_be_reported() -> None:
    assert report.count(0) == "0"


def test_closed_h2_nominal_not_decision() -> None:
    row = fixture_window()["summary"]["jump_secondary"]["contrasts"][1]
    assert "sólo diagnóstico" in report.sequence_text(row)
    bad = copy.deepcopy(fixture_window())
    bad["summary"]["jump_secondary"]["contrasts"][1]["p_for_decision"] = 0.8
    with pytest.raises(ValueError, match="JUMP_SEQUENCE_P"):
        validate(bad)


def test_validated_old_high_gradient_does_not_trigger_refit() -> None:
    bundle = fixture_window()
    rows = validate(bundle)
    old = [r for r in rows if r["provenance"] == "REUSED_FROZEN_V3"]
    assert sum(r["gradients_above_tolerance"] for r in old) == 18
    assert sum(r["certified"] for r in old) == 0


def test_missing_old_gradient_remains_unknown() -> None:
    fits = fixture_window()["fits"]
    fits[0]["fit"]["solver_refit"].pop("gradient_inf_norm_objective_over_n")
    rows = report.certificate_counts(fits)
    old = next(r for r in rows if r["provenance"] == "REUSED_FROZEN_V3" and r["phase"] == "refit")
    assert old["gradients_unavailable"] == 1
    assert old["gradients_available"] == 2


def test_new_logit_cannot_claim_certificate_from_solver_success_only() -> None:
    fits = fixture_window()["fits"]
    fits[6]["fit"]["solver_refit"].pop("original_gradient_certificate_applicable")
    with pytest.raises(ValueError, match="NEW_CERTIFICATE_MISSING"):
        report.certificate_counts(fits)


def test_new_logit_certificate_gradient_failure() -> None:
    fits = fixture_window()["fits"]
    fits[6]["fit"]["solver_refit"]["gradient_inf_norm_objective_over_n"] = 1e-5
    with pytest.raises(ValueError, match="NEW_GRADIENT_CERTIFICATE"):
        report.certificate_counts(fits)


def test_new_logit_certificate_objective_failure() -> None:
    fits = fixture_window()["fits"]
    fits[6]["fit"]["solver_refit"]["literal_original_objective_abs_difference"] = 0.1
    with pytest.raises(ValueError, match="NEW_OBJECTIVE_CERTIFICATE"):
        report.certificate_counts(fits)


def test_new_single_class_exception_not_fake_zero_gradient() -> None:
    fits = fixture_window()["fits"]
    fits[6]["fit"]["solver_refit"] = {
        "converged": True,
        "original_gradient_certificate_applicable": False,
        "numerical_repair": "unchanged_single_class_exception",
    }
    rows = report.certificate_counts(fits)
    new = next(
        r for r in rows if r["provenance"] == "NEW_MISSING_COMPONENT" and r["phase"] == "refit"
    )
    assert new["single_class_exceptions"] == 1
    assert new["gradients_unavailable"] == 1
    assert new["certified"] == 2


@pytest.mark.parametrize(
    "mutator,reason",
    [
        (lambda b: b["summary"].update(status="RUNNING"), "INCOMPLETE_ATTEMPTS"),
        (lambda b: b["summary"]["binding"].update(release_sha256="f" * 64), "SUMMARY_BINDING"),
        (lambda b: b["summary"].update(primary_changed=True), "SCOPE_DRIFT"),
        (lambda b: b["summary"]["resources"].update(threads_total_max=4), "THREAD_CAP"),
        (lambda b: b["summary"]["resources"].update(priority="32"), "LOW_PRIORITY"),
        (lambda b: b["summary"]["component_counts"][0].update(N=None), "COUNT_INVALID"),
        (
            lambda b: b["components"][0].update(original_component_sha256="f" * 64),
            "REUSED_COMPONENT_DRIFT",
        ),
    ],
)
def test_binding_scope_resource_and_provenance_guards(mutator: Any, reason: str) -> None:
    bundle = fixture_window()
    mutator(bundle)
    with pytest.raises(ValueError, match=reason):
        validate(bundle)


def test_unknown_auc_displayed_without_inventing_zero() -> None:
    evidence = fixture_evidence()
    row = evidence["windows"]["primary"]["summary"]["jump_secondary"]["families"][0]["auc"]["B0"]
    row.update(
        estimate=None, ci_low=None, ci_high=None, status="NO VERIFICABLE", reason="monoclase"
    )
    rendered = report.render(evidence).decode()
    assert "B0 | NO VERIFICABLE | [NO VERIFICABLE, NO VERIFICABLE]" in rendered
    assert "monoclase" in rendered
    assert "MZ: NO VERIFICABLE" in rendered


def test_failure_metadata_is_retained_in_rendered_report() -> None:
    evidence = fixture_evidence()
    row = evidence["windows"]["primary"]["fits"][6]
    row.update(status="NO VERIFICABLE", failure={"reason": "LOGISTIC_REPAIR: maxiter"}, fit={})
    evidence["windows"]["primary"]["certificates"] = report.certificate_counts(
        evidence["windows"]["primary"]["fits"]
    )
    rendered = report.render(evidence).decode()
    assert "LOGISTIC_REPAIR: maxiter" in rendered
    assert "Cero componentes fallidos" not in rendered


def test_existing_report_prevents_any_read_or_overwrite(tmp_path: Path, monkeypatch: Any) -> None:
    path = tmp_path / report.REPORT
    path.parent.mkdir(parents=True)
    path.write_bytes(b"KEEP")
    monkeypatch.setattr(report, "load_evidence", lambda *args: pytest.fail("must not load"))
    with pytest.raises(ValueError, match="OUTPUT_ALREADY_EXISTS"):
        report.execute(tmp_path, tmp_path / "private", "d" * 64, {}, "synthetic")
    assert path.read_bytes() == b"KEEP"


def test_no_fit_or_inference_entrypoint_is_called() -> None:
    tree = ast.parse(Path(report.__file__).read_text(encoding="utf-8"))
    calls = [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
    forbidden = (
        "_jump",
        "aggregate",
        "fit_jump_linear",
        "fit_jump_lightgbm",
        "minimize",
        "pooled_auc_inference",
        "family_fixed_sequence",
        "read_parquet",
    )
    assert not any(call.split(".")[-1] in forbidden for call in calls)
