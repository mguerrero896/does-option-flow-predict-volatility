"""Close v3 secondaries from two completed receipts; never fit or recompute inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from artifacts.rp4_code.evaluate import sha256, write_bytes_once, write_json_once
from artifacts.rp4_v3_code.report_v3 import family_label, number, table
from artifacts.rp4_v3_code.report_v3 import read_json as read_json

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = Path("private-input/e90b04c9636db3ce4b5d")
FOLDER = Path("artifacts/rp4_v3_secondary_closeout")
REPORT = Path("docs/rp4/results_v3_revision2.md")
WINDOWS = {"primary": "Primaria", "confirmation": "Confirmación"}
FAMILIES = ("log_ridge_harq", "lightgbm_qlike")
SETS = ("B0", "B1", "B2")
PROVENANCES = ("REUSED_FROZEN_V3", "NEW_MISSING_COMPONENT")
MODELS = tuple(f"jump__{family}__{name}" for family in FAMILIES for name in SETS)
ADDENDUM_SHA = "606a8c8d5dbe51628e7507b504cf7c5f8483a9aa5e7c80f62be33b2cb12e55de"
INVENTORY_SHA = "a7f0bd85aa2d817cfc7d1da7b463fc7c8751ee7e966b13fb662a63e403731c38"
SPEC_SHA = "930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5"
ORIGINAL_RELEASE_SHA = "5e3046af023c9f41380307d62537aa4e8fc7514b23d51a95ea1f960ee23fe5bb"
FROZEN_PINS = {
    "docs/rp4/results_v3_revision1.md": (
        "f209a54519298d8ee7308a8dc20b5c293d0da4fbad807709aed8aca2feb1db03"  # Original report.
    ),
    "artifacts/rp4_v3_b2/summary.json": (
        "645d319f4b5b283a2b1bc6ecda1a185650b8436cdbf3b319e9debfc41210ef1d"  # Primary.
    ),
    "artifacts/rp4_v3_b3/summary.json": (
        "64af964691d1127df7b3e2e0f05395c810719f2fe4e5ba3fa0207fcc8e15591b"  # Confirmation.
    ),
    "artifacts/rp4_v3_secondary_repair/addendum.json": ADDENDUM_SHA,
    "docs/rp4/v3_secondary_implementation_addendum_v1.md": (
        "c89b63598f9d9a2aff2a76e0f09ed303653ffac83f8c4e5d50f128dcc04dafd7"  # Before fits.
    ),
    "artifacts/rp4_v3_b4/mz_identity_receipt.json": (
        "cdce9bb0b4e82db62492034e3911748b8cc5bc4176f2e55ca49ad5264e993eb4"  # Primary MZ.
    ),
    "artifacts/rp4_v3_secondary_mz_audit/confirmation_summary.json": (
        "c185a396d59c35b5be81cc09406541c67c33dc60de80e713657b7283b66f9b71"  # Closed audit.
    ),
    "artifacts/rp4_v3_secondary_mz_audit/receipt.json": (
        "ebe38763e180d6676e57d13fd65b22df2f9ec537985d8768466ffb7434ee6b4b"  # No refits.
    ),
    "artifacts/rp4_v3_secondary_mz_audit/manifest.json": (
        "9b7b88bfead2ba3018d8ce8bd4b4739679a4418bde752818fa6f76f1ebf2a42a"  # Audit pins.
    ),
    "artifacts/rp4_v3_secondary_mz_audit/REPORT.md": (
        "06aaa5ca529f3d3f9ce4fc1716e54ffcede848d91062b8e3c168649480bffa30"  # Cause proof.
    ),
    "artifacts/rp4_v3_a2/evaluation_release.json": ORIGINAL_RELEASE_SHA,
    "artifacts/rp4_v3_a1_empty_window/specification.json": SPEC_SHA,
}
PRIMARY_HEADER = (
    "| Ventana | Familia | Contraste | Delta | IC95% | Reducción % | "
    "p unilateral nominal | Decisión | N sesiones/orígenes |"
).encode()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError("RP4_V3_REVISION2_" + reason)


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def count(value: Any) -> str:
    """Unavailable counts are not empty sets and must never be rendered as zero."""
    return (
        str(int(value))
        if finite(value) and value >= 0 and int(value) == value
        else "NO VERIFICABLE"
    )


def integer(value: Any, reason: str) -> int:
    require(count(value) != "NO VERIFICABLE", reason)
    return int(value)


def primary_block(encoded: bytes) -> bytes:
    """Extract the original table bytes including its original newline convention."""
    lines = encoded.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip(b"\r\n") == PRIMARY_HEADER]
    require(len(starts) == 1, "PRIMARY_HEADER")
    start = starts[0]
    end = start + 1
    while end < len(lines) and lines[end].startswith(b"|"):
        end += 1
    require(end - start == 10, "PRIMARY_EIGHT_ROWS_REQUIRED")
    return b"".join(lines[start:end])


def verify_primary_table(block: bytes, summaries: dict[str, dict[str, Any]]) -> None:
    rows = [line.decode().strip().strip("|").split("|") for line in block.splitlines()[2:]]
    expected = [
        (window, family, contrast)
        for window in WINDOWS
        for family in FAMILIES
        for contrast in ("B1_over_B0", "B2_over_B1")
    ]
    require(len(rows) == len(expected), "PRIMARY_ROW_COUNT")
    for fields, (window, family, contrast) in zip(rows, expected, strict=True):
        fields = [field.strip() for field in fields]
        records = summaries[window]["contrasts"]
        selected = [r for r in records if (r["family"], r["contrast"]) == (family, contrast)]
        require(len(selected) == 1 and len(fields) == 9, "PRIMARY_CONTRAST_KEY")
        row = selected[0]
        require(
            row.get("endpoint") == "qlike_mean"
            and row.get("inference_role") == "PRIMARY"
            and row.get("statistic") == "mean",
            "PRIMARY_ROLE",
        )
        require(
            fields[:3]
            == [
                WINDOWS[window],
                "Ridge" if family == FAMILIES[0] else "LightGBM",
                "B1/B0" if contrast == "B1_over_B0" else "B2/B1",
            ]
            and fields[3] == f"{row['estimate']:+.10f}"
            and fields[4] == f"[{row['ci_low']:.10f}, {row['ci_high']:.10f}]"
            and fields[5] == f"{row['qlike_reduction_percent']:+.7f}"
            and fields[6] == f"{row['p_raw']:.4f}"
            and fields[8] == f"{row['N_sessions']}/{row['N_origins']}",
            "PRIMARY_DISPLAY_VALUE_DRIFT",
        )


def verified(path: Path, expected: str, pins: dict[str, str]) -> Any:
    require(len(expected) == 64 and all(c in "0123456789abcdef" for c in expected), "INVALID_SHA")
    require(path.is_file() and sha256(path) == expected, "HASH_DRIFT:" + str(path))
    pins[str(path.resolve())] = expected
    return read_json(path) if path.suffix == ".json" else None


def check_sequence(rows: list[dict[str, Any]]) -> None:
    require(len(rows) == 4, "JUMP_FOUR_CONTRASTS")
    require(
        {(r["family"], r["contrast"]) for r in rows}
        == {(f, c) for f in FAMILIES for c in ("B1_over_B0", "B2_over_B1")},
        "JUMP_CONTRAST_KEYS",
    )
    for family in FAMILIES:
        opened = True
        for contrast in ("B1_over_B0", "B2_over_B1"):
            row = next(r for r in rows if (r["family"], r["contrast"]) == (family, contrast))
            require(
                row["endpoint"] == "jump_auc" and row["inference_role"] == "SECONDARY", "JUMP_ROLE"
            )
            available = row.get("status") == "COMPUTED" and all(
                finite(row.get(k)) for k in ("estimate", "ci_low", "ci_high", "p_raw")
            )
            reject = bool(opened and available and row["estimate"] > 0 and row["p_raw"] <= 0.05)
            status = (
                "NOT_TESTED"
                if not opened
                else "NO_VERIFICABLE"
                if not available
                else "REJECTED"
                if reject
                else "NOT_REJECTED"
            )
            require(
                row["hypothesis_status"] == status and row["rejected"] is reject,
                "JUMP_SEQUENCE_STATE",
            )
            expected_p = row["p_raw"] if opened and available else None
            require(row.get("p_for_decision") == expected_p, "JUMP_SEQUENCE_P")
            opened = reject


def certificate_counts(fits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Census saved diagnostics; do not optimize or evaluate model predictions."""
    rows = []
    for provenance in PROVENANCES:
        selected = [
            r
            for r in fits
            if r["provenance"] == provenance
            and "__log_ridge_harq__" in r["model"]
            and r["status"] == "COMPUTED"
        ]
        for phase in ("refit", "candidate"):
            solvers = (
                [r["fit"]["solver_refit"] for r in selected]
                if phase == "refit"
                else [c["solver"] for r in selected for c in r["fit"]["candidates"]]
            )
            available = [
                s.get("gradient_inf_norm_objective_over_n")
                for s in solvers
                if finite(s.get("gradient_inf_norm_objective_over_n"))
            ]
            certified, single_class, unavailable = 0, 0, 0
            for solver in solvers:
                if provenance == "REUSED_FROZEN_V3":
                    unavailable += 1  # Old convergence is not a new gradient certificate.
                elif solver.get("original_gradient_certificate_applicable") is True:
                    require(solver.get("converged") is True, "NEW_UNCONVERGED_LOGIT")
                    gradient = solver.get("gradient_inf_norm_objective_over_n")
                    require(finite(gradient) and gradient <= 1e-8, "NEW_GRADIENT_CERTIFICATE")
                    names = (
                        "stable_gradient_inf_norm",
                        "objective_total_divided_by_n",
                        "objective_initial_divided_by_n",
                        "literal_original_objective_abs_difference",
                        "literal_original_gradient_max_abs_difference",
                    )
                    require(all(finite(solver.get(k)) for k in names), "NEW_CERTIFICATE_NONFINITE")
                    objective = solver["objective_total_divided_by_n"]
                    require(
                        solver["stable_gradient_inf_norm"] <= 1e-8
                        and objective <= solver["objective_initial_divided_by_n"] + 1e-12
                        and solver["literal_original_objective_abs_difference"]
                        <= 1e-10 * max(1.0, abs(objective))
                        and solver["literal_original_gradient_max_abs_difference"] <= 1e-10,
                        "NEW_OBJECTIVE_CERTIFICATE",
                    )
                    certified += 1
                elif solver.get("original_gradient_certificate_applicable") is False:
                    require(
                        solver.get("numerical_repair") == "unchanged_single_class_exception"
                        and solver.get("converged") is True,
                        "INVALID_SINGLE_CLASS_EXCEPTION",
                    )
                    single_class += 1
                else:
                    raise ValueError("RP4_V3_REVISION2_NEW_CERTIFICATE_MISSING")
            rows.append(
                {
                    "provenance": provenance,
                    "phase": phase,
                    "N_solvers": len(solvers),
                    "gradients_available": len(available),
                    "gradients_unavailable": len(solvers) - len(available),
                    "gradients_above_tolerance": sum(v > 1e-8 for v in available),
                    "gradient_max": max(available) if available else None,
                    "certified": certified,
                    "single_class_exceptions": single_class,
                    "certificate_not_applied": unavailable,
                    "solver_converged": sum(s.get("converged") is True for s in solvers),
                    "solver_convergence_unknown": sum("converged" not in s for s in solvers),
                }
            )
    return rows


def validate_window(
    summary: dict[str, Any],
    fits: list[dict[str, Any]],
    components: list[dict[str, Any]],
    plan: dict[str, Any],
    release_sha: str,
) -> list[dict[str, Any]]:
    window = plan["window"]
    require(summary["status"] == "COMPLETE_SECONDARY_ATTEMPTS", "INCOMPLETE_ATTEMPTS")
    require(
        summary["binding"] == {"release_sha256": release_sha, "window": window, "endpoint": "jump"},
        "SUMMARY_BINDING",
    )
    for name in ("primary_changed", "quantile_changed", "mz_changed", "capital_go"):
        require(summary.get(name) is False, "SCOPE_DRIFT:" + name)
    require(summary.get("RESEARCH_ONLY") is True, "RESEARCH_SCOPE")
    sessions = {r["session"] for r in plan["sessions"]}
    expected = {(session, model) for session in sessions for model in MODELS}
    require(summary["scheduled_sessions"] == len(sessions) == plan["N_sessions"], "SESSION_COUNT")
    require(set(summary["session_sha256"]) == {s + ".json" for s in sessions}, "SESSION_SET")
    require(len(fits) == len(components) == len(expected), "COMPONENT_COUNT")
    for source in (fits, components):
        require({(r["session"], r["model"]) for r in source} == expected, "COMPONENT_KEYS")
    keyed = {(r["session"], r["model"]): r for r in components}
    original = {(r["session"], r["model"]): r for r in plan["components"]}
    for row in fits:
        key = row["session"], row["model"]
        item = keyed[key]
        require(row["status"] in ("COMPUTED", "NO VERIFICABLE"), "COMPONENT_STATUS")
        require(
            (row["provenance"], row["status"]) == (item["provenance"], item["status"]),
            "FIT_MANIFEST_DRIFT",
        )
        require(
            row["provenance"] == (PROVENANCES[0] if key in original else PROVENANCES[1]),
            "REUSE_CLASSIFICATION",
        )
        if key in original:
            require(
                row["status"] == "COMPUTED"
                and item["original_component_sha256"] == original[key]["component_sha256"],
                "REUSED_COMPONENT_DRIFT",
            )
        else:
            require(item["original_component_sha256"] is None, "NEW_COMPONENT_FALSE_SOURCE")
    expected_counts = Counter((r["provenance"], r["status"]) for r in fits)
    reported_counts = {
        (r["provenance"], r["status"]): integer(r["N"], "COUNT_INVALID")
        for r in summary["component_counts"]
    }
    require(
        len(reported_counts) == len(summary["component_counts"])
        and dict(expected_counts) == reported_counts,
        "COMPONENT_CENSUS_DRIFT",
    )
    for provenance, name in zip(
        PROVENANCES, ("reusable_components", "missing_components"), strict=True
    ):
        require(
            sum(n for (p, _), n in expected_counts.items() if p == provenance) == plan[name],
            "INVENTORY_TOTAL_DRIFT",
        )
    resources = summary["resources"]
    require(resources["threads_total_max"] == 2, "THREAD_CAP")
    require(
        str(resources["priority"])
        in ("16384", "64", "BELOW_NORMAL_PRIORITY_CLASS", "IDLE_PRIORITY_CLASS"),
        "LOW_PRIORITY_NOT_VERIFIED",
    )
    require(
        all(integer(p["num_threads"], "THREAD_COUNT") <= 2 for p in resources["threadpools"]),
        "THREAD_POOL_CAP",
    )
    require(
        resources.get("arrow_cpu_threads") == 2
        and resources.get("arrow_io_threads") == 1
        and resources.get("parquet_use_threads") is False,
        "ARROW_RESOURCE_CAP",
    )
    jump = summary["jump_secondary"]
    require(jump["endpoint"] == "jump_auc" and jump["inference_role"] == "SECONDARY", "ENDPOINT")
    require(jump["status"] in ("COMPUTED", "NO VERIFICABLE"), "JUMP_STATUS")
    excluded = {r["session"] for r in jump["excluded_sessions"]}
    failures = {r["session"] for r in fits if r["status"] == "NO VERIFICABLE"}
    require(
        excluded == failures and len(excluded) == len(jump["excluded_sessions"]),
        "EXCLUSION_CENSUS_DRIFT",
    )
    included = sessions - excluded
    expected_n = sum(r["N_jump_origins"] for r in plan["sessions"] if r["session"] in included)
    require(jump["N_sessions"] == len(included) and jump["N_origins"] == expected_n, "JUMP_N")
    require(
        len(jump["families"]) == 2 and {r["family"] for r in jump["families"]} == set(FAMILIES),
        "JUMP_FAMILIES",
    )
    for family in jump["families"]:
        require(
            set(family["auc"]) == set(SETS)
            and family["N_sessions"] == len(included)
            and family["N_origins"] == expected_n,
            "AUC_KEYS_OR_N",
        )
        for metric in family["auc"].values():
            if metric["status"] == "COMPUTED":
                require(
                    all(
                        finite(metric.get(k)) and 0 <= metric[k] <= 1
                        for k in ("estimate", "ci_low", "ci_high")
                    ),
                    "COMPUTED_AUC_NONFINITE",
                )
    check_sequence(jump["contrasts"])
    require(
        jump["sequence"]["contrasts"] == jump["contrasts"]
        and jump["sequence"]["scope"] == "SECONDARY_ENDPOINT_JOINT",
        "SEQUENCE_SOURCE_DRIFT",
    )
    certificate_rows = certificate_counts(fits)
    for provenance in PROVENANCES:
        matching = [r for r in summary["gradient_diagnostics"] if r["provenance"] == provenance]
        require(len(matching) == 1, "GRADIENT_CENSUS_KEYS")
        reported = matching[0]
        for row in (r for r in certificate_rows if r["provenance"] == provenance):
            label = row["phase"]
            for gradient_key, expected_value in {
                f"{label}_gradients_available": row["gradients_available"],
                f"{label}_gradients_missing_or_single_class": row["gradients_unavailable"],
                f"{label}_gradients_above_1e_minus8": row["gradients_above_tolerance"],
                f"{label}_gradient_max": row["gradient_max"],
            }.items():
                require(
                    reported.get(gradient_key) == expected_value,
                    "GRADIENT_CENSUS_VALUE:" + gradient_key,
                )
    return certificate_rows


def load_evidence(
    root: Path, private: Path, release_sha: str, receipt_shas: dict[str, str]
) -> dict[str, Any]:
    pins: dict[str, str] = {}
    # Both closure receipts are verified before either new AUC summary is opened.
    receipts = {}
    for window in WINDOWS:
        path = private / "evaluation" / window / "receipt.json"
        receipt = verified(path, receipt_shas[window], pins)
        require(
            receipt["status"] == "COMPLETE"
            and receipt["exit_code"] == 0
            and receipt["window"] == window
            and receipt["release_sha256"] == release_sha,
            "WINDOW_NOT_CLOSED:" + window,
        )
        receipts[window] = receipt
    release = verified(private / "jump_release.json", release_sha, pins)
    require(
        release["addendum_sha256"] == ADDENDUM_SHA
        and release["inventory_sha256"] == INVENTORY_SHA
        and release["specification_sha256"] == SPEC_SHA
        and release["original_release_sha256"] == ORIGINAL_RELEASE_SHA
        and release["endpoint"] == "jump_only"
        and release["threads_total_max"] == 2
        and release["reusable_components"] == 962
        and release["missing_components"] == 1702,
        "RELEASE_CONTRACT",
    )
    for relative, digest in FROZEN_PINS.items():
        verified(root / relative, digest, pins)
    for relative, digest in release["code_sha256"].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root), "SOURCE_PATH_ESCAPE")
        verified(path, digest, pins)
    original = {
        window: read_json(root / f"artifacts/rp4_v3_{stage}/summary.json")
        for window, stage in (("primary", "b2"), ("confirmation", "b3"))
    }
    block = primary_block((root / "docs/rp4/results_v3_revision1.md").read_bytes())
    verify_primary_table(block, original)
    inventory = verified(private / "jump_inventory.json", INVENTORY_SHA, pins)
    require(
        inventory["status"] == "VERIFIED"
        and inventory["reusable_components"] == 962
        and inventory["missing_components"] == 1702,
        "INVENTORY_STATUS",
    )
    # Revalidate the pinned original receipts/artifacts without reading forecasts or targets.
    for filename, digest in inventory["input_sha256"].items():
        path = Path(filename).resolve()
        require(
            path.is_relative_to(root)
            or path.is_relative_to(Path("private-input/e63a7488cbab65e3773b")),
            "ORIGINAL_INPUT_PATH",
        )
        require(path.is_file() and sha256(path) == digest, "ORIGINAL_INPUT_HASH:" + filename)
        pins[str(path)] = digest
    windows = {}
    for window in WINDOWS:
        folder = private / "evaluation" / window
        receipt = receipts[window]
        require(receipt["code_sha256"] == release["code_sha256"], "RECEIPT_CODE_DRIFT")
        required = {
            folder / name
            for name in (
                "summary.json",
                "fit_diagnostics.json",
                "component_manifest.json",
                "summary_receipt.json",
            )
        }
        artifacts = {Path(p).resolve(): digest for p, digest in receipt["artifacts_sha256"].items()}
        require(set(artifacts) == {p.resolve() for p in required}, "RECEIPT_ARTIFACT_SET")
        values = {p.name: verified(p, digest, pins) for p, digest in artifacts.items()}
        log = Path(receipt["log"]).resolve()
        require(log.is_relative_to(private), "LOG_PATH_ESCAPE")
        verified(log, receipt["log_sha256"], pins)
        summary = values["summary.json"]
        child = values["summary_receipt.json"]
        require(
            child["binding"] == summary["binding"]
            and set(child["artifacts_sha256"])
            == {"summary.json", "fit_diagnostics.json", "component_manifest.json"},
            "SUMMARY_RECEIPT_BINDING",
        )
        require(
            all(
                child["artifacts_sha256"][name] == artifacts[(folder / name).resolve()]
                for name in child["artifacts_sha256"]
            ),
            "SUMMARY_RECEIPT_HASH",
        )
        require(
            receipt["summary_sha256"] == artifacts[(folder / "summary.json").resolve()],
            "SUMMARY_TOPLEVEL_SHA",
        )
        plan = next(r for r in inventory["windows"] if r["window"] == window)
        fits, components = values["fit_diagnostics.json"], values["component_manifest.json"]
        certificates = validate_window(summary, fits, components, plan, release_sha)
        for name, digest in summary["session_sha256"].items():
            path = folder / "sessions" / name
            require(
                Path(name).name == name and path.is_file() and sha256(path) == digest,
                "SESSION_HASH_DRIFT",
            )
        for row in components:
            for kind, key in (
                ("components", "component_sha256"),
                ("component_receipts", "receipt_sha256"),
            ):
                path = folder / kind / row["session"] / (row["model"] + ".json")
                require(path.is_file() and sha256(path) == row[key], "COMPONENT_PHYSICAL_HASH")
        windows[window] = {
            "summary": summary,
            "receipt": receipt,
            "certificates": certificates,
            "fits": fits,
            "plan": plan,
        }
    require(
        datetime.fromisoformat(receipts["primary"]["completed_at_utc"])
        <= datetime.fromisoformat(receipts["confirmation"]["started_at_utc"]),
        "WINDOW_RESOURCE_OVERLAP",
    )
    return {
        "primary_block": block,
        "original": original,
        "windows": windows,
        "release_sha256": release_sha,
        "pins": pins,
        "inventory": inventory,
        "mz_primary": read_json(root / "artifacts/rp4_v3_b4/mz_identity_receipt.json")["stdout"],
        "mz_confirmation": read_json(
            root / "artifacts/rp4_v3_secondary_mz_audit/confirmation_summary.json"
        ),
    }


def interval(row: dict[str, Any]) -> str:
    return f"[{number(row.get('ci_low'))}, {number(row.get('ci_high'))}]"


def sequence_text(row: dict[str, Any]) -> str:
    return {
        "REJECTED": "Rechazada (secundaria)",
        "NOT_REJECTED": "No rechazada",
        "NOT_TESTED": "H2 no abierta; p crudo sólo diagnóstico",
        "NO_VERIFICABLE": "NO VERIFICABLE",
    }[row["hypothesis_status"]]


def render(evidence: dict[str, Any]) -> bytes:
    """Pure presentation of already-stored numbers; accepts synthetic evidence in tests."""
    original_block: bytes = evidence["primary_block"]
    mz_receipt_sha = FROZEN_PINS["artifacts/rp4_v3_secondary_mz_audit/receipt.json"]
    parts = [
        "# RP4 v3 — cierre B4, revisión de secundarios 2",
        "",
        "Esta revisión cierra los intentos secundarios de salto de ambas ventanas. "
        "No cambia los resultados primarios, cuantiles, máscaras, ventanas ni la "
        "recalibración MZ. Las tablas completas v1/v2/v3, cobertura, regímenes, extremos "
        "y figuras permanecen en el [informe original](results_v3.md).",
        "",
        "fuera de muestra walk-forward, partición fijada 2026-09-07.",
        "",
        "## Resultado primario sin cambios",
        "",
        "Delta = QLIKE base menos ampliado; reducción = 100 × delta / QLIKE base. "
        "IC95% bilateral por bloques; p unilateral de la secuencia H1 → H2. "
        "Las ocho filas siguientes se conservan byte a byte de la revisión 1; los "
        "dos agregados originales se verifican por SHA-256.",
        "",
    ]
    prefix = ("\n".join(parts) + "\n").encode()
    suffix = [
        "",
        "Fuente: [primaria original](../../artifacts/rp4_v3_b2/summary.json) y "
        "[confirmación original](../../artifacts/rp4_v3_b3/summary.json). La conjunción "
        "primaria registrada no se satisface en ninguna ventana. Ningún secundario "
        "sustituye la media ni convierte estas ventanas en una réplica independiente.",
        "",
        "## Salto: AUC fuera de muestra y contrastes secundarios",
        "",
        "Objetivo: indicador jump30 > 0 (exceso RV−BPV positivo, no un test formal "
        "de salto). AUC agrupada por origen, peso uno y empates 0,5. Delta = AUC "
        "rica menos AUC base. IC95% y p proceden del agregado de salto v3, con "
        "9.999 remuestreos de bloques de sesiones y secuencia H1 → H2 por familia. "
        "No se recalcula inferencia en este informe. Una réplica monoclase invalida "
        "los IC/p, sin redibujarla ni convertir lo no verificable en cero.",
        "",
    ]
    auc_rows, contrast_rows, census_rows, gradient_rows, resource_rows, failure_rows = (
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for window, label in WINDOWS.items():
        bundle = evidence["windows"][window]
        summary, receipt = bundle["summary"], bundle["receipt"]
        jump = summary["jump_secondary"]
        for family in jump["families"]:
            for name in SETS:
                row = family["auc"][name]
                auc_rows.append(
                    [
                        label,
                        family_label(family["family"], "jump"),
                        name,
                        number(row.get("estimate")),
                        interval(row),
                        count(family.get("N_sessions")),
                        count(family.get("N_origins")),
                        count(family.get("invalid_class_resamples")),
                        row["status"],
                        row.get("reason", "—"),
                    ]
                )
        for row in jump["contrasts"]:
            contrast_rows.append(
                [
                    label,
                    family_label(row["family"], "jump"),
                    row["contrast"].replace("_over_", "/"),
                    number(row.get("estimate"), signed=True),
                    interval(row),
                    number(row.get("p_raw")),
                    number(row.get("p_for_decision")),
                    sequence_text(row),
                    count(row.get("N_sessions")),
                    count(row.get("N_origins")),
                ]
            )
        # Counts are derived from the validated complete manifest, including failed attempts.
        for provenance in PROVENANCES:
            group = [r for r in bundle["fits"] if r["provenance"] == provenance]
            for family in FAMILIES:
                rows = [r for r in group if f"__{family}__" in r["model"]]
                census_rows.append(
                    [
                        label,
                        family_label(family, "jump"),
                        provenance,
                        str(len(rows)),
                        str(sum(r["status"] == "COMPUTED" for r in rows)),
                        str(sum(r["status"] == "NO VERIFICABLE" for r in rows)),
                    ]
                )
        for row in bundle["certificates"]:
            gradient_rows.append(
                [
                    label,
                    row["provenance"],
                    row["phase"],
                    *[
                        count(row.get(k))
                        for k in (
                            "N_solvers",
                            "solver_converged",
                            "solver_convergence_unknown",
                            "gradients_available",
                            "gradients_unavailable",
                            "gradients_above_tolerance",
                        )
                    ],
                    number(row.get("gradient_max")),
                    *[
                        count(row.get(k))
                        for k in ("certified", "single_class_exceptions", "certificate_not_applied")
                    ],
                ]
            )
        for row in bundle["fits"]:
            if row["status"] == "NO VERIFICABLE":
                reason = (row.get("failure") or {}).get("reason", "NO VERIFICABLE: sin causa")
                failure_rows.append([label, row["session"], row["model"], reason])
        resources = summary["resources"]
        resource_rows.append(
            [
                label,
                str(resources["threads_total_max"]),
                str(resources["priority"]),
                str(resources["process_id"]),
                count(receipt.get("exit_code")),
                number(receipt.get("elapsed_seconds")),
                str(receipt["started_at_utc"]),
                str(receipt["completed_at_utc"]),
            ]
        )
    suffix += [
        table(
            [
                "Ventana",
                "Familia",
                "Conjunto",
                "AUC",
                "IC95%",
                "N sesiones",
                "N orígenes",
                "Réplicas monoclase",
                "Estado",
                "Motivo",
            ],
            auc_rows,
        ),
        "",
        table(
            [
                "Ventana",
                "Familia",
                "Contraste",
                "Delta AUC",
                "IC95%",
                "p crudo unilateral",
                "p de decisión secuencial",
                "Decisión secundaria",
                "N sesiones",
                "N orígenes",
            ],
            contrast_rows,
        ),
        "",
        "Una H2 no abierta conserva el p crudo como diagnóstico; no tiene p de decisión "
        "secuencial. Una AUC puntual disponible no implica que su intervalo sea verificable.",
        "",
    ]
    for window, label in WINDOWS.items():
        jump = evidence["windows"][window]["summary"]["jump_secondary"]
        suffix += [
            f"{label}: {count(jump.get('N_sessions'))} sesiones y "
            f"{count(jump.get('N_origins'))} orígenes comparables; "
            f"{count(jump.get('positive_labels'))} etiquetas positivas y "
            f"{count(jump.get('negative_labels'))} negativas. "
            f"Sesiones excluidas sólo del salto: {len(jump['excluded_sessions'])}.",
            "",
        ]
    suffix += [
        "## Alcance de la reparación y convergencia",
        "",
        "El [addendum de implementación](v3_secondary_implementation_addendum_v1.md), "
        f"con registro JSON SHA-256 `{ADDENDUM_SHA}`, se congeló antes de nuevos ajustes "
        "secundarios. Se reutilizan 962 componentes ya completos (912 de primaria, "
        "50 de confirmación). Sólo se intentan los 1.702 faltantes: 801 logit y 801 "
        "LightGBM en primaria; 50 y 50 en confirmación. Intento terminado no significa "
        "ajuste exitoso: las fallas se conservan abajo.",
        "",
        "La corrección logit es un precondicionamiento invertible de Fisher con el mismo "
        "objetivo, las cinco lambdas y la selección en las diez últimas sesiones de "
        "entrenamiento. El certificado nuevo exige gradiente original ≤1e-8 y "
        "equivalencia algebraica; no se acepta sólo el éxito declarado por el optimizador. "
        "Se conserva la excepción registrada para entrenamiento monoclase. Los componentes "
        "viejos se reutilizan bajo su contrato de convergencia original: un gradiente "
        "viejo mayor al umbral nuevo se revela, no se oculta ni provoca un refit adicional.",
        "",
        table(
            ["Ventana", "Familia", "Procedencia", "Componentes", "COMPUTED", "NO VERIFICABLE"],
            census_rows,
        ),
        "",
        table(
            [
                "Ventana",
                "Procedencia",
                "Fase",
                "Solvers",
                "Convergencia declarada",
                "Convergencia desconocida",
                "Gradientes disponibles",
                "Gradientes ausentes",
                "Gradiente >1e-8",
                "Gradiente máximo",
                "Certificados nuevos",
                "Excepciones monoclase",
                "Certificado nuevo no aplicado",
            ],
            gradient_rows,
        ),
        "",
        "Los gradientes ausentes no se interpretan como cero. El certificado nuevo no "
        "se atribuye retroactivamente a los componentes congelados.",
        "",
        "### Fallos de componentes y recursos",
        "",
        (
            table(["Ventana", "Sesión", "Componente", "Causa preservada"], failure_rows)
            if failure_rows
            else "Cero componentes fallidos, comprobado contra los manifiestos completos."
        ),
        "",
        table(
            [
                "Ventana",
                "Máximo hilos de cálculo",
                "Prioridad Windows",
                "PID",
                "Código de salida",
                "Segundos",
                "Inicio UTC",
                "Fin UTC",
            ],
            resource_rows,
        ),
        "",
        "Las ventanas se ejecutaron secuencialmente, con límite de dos hilos de cálculo "
        "y prioridad baja, sin cambiar ni interrumpir la evaluación v4. Este generador "
        "sólo lee agregados y metadatos cerrados, con un hilo; no ajusta modelos ni "
        "recalcula predicciones o estadística inferencial.",
        "",
        "## MZ: NO VERIFICABLE como recalibración utilizable",
        "",
        "No se demostró un error aritmético: la recta afín, el fallback y el piso 1e-12 "
        "reproducen los pronósticos guardados. El problema observado es que la recta "
        "produce valores negativos en algunos orígenes y el piso positivo dispara QLIKE. "
        "No se cambió fórmula, escala, intercepto ni piso para ocultar esa inestabilidad. "
        "Los números siguientes son exclusivamente el diagnóstico auditado, no resultados "
        "de una recalibración corregida.",
        "",
    ]
    mz_rows = []
    for window, source in (
        ("primary", evidence["mz_primary"]),
        ("confirmation", evidence["mz_confirmation"]),
    ):
        for name in SETS:
            row = source["results"][name]
            mz_rows.append(
                [
                    WINDOWS[window],
                    name,
                    number(row.get("raw_qlike_recomputed")),
                    number(row.get("mz_qlike_recomputed")),
                    count(row.get("N_origins")),
                    count(row.get("strictly_negative_affine")),
                    count(row.get("floor_hits")),
                    number(row.get("floor_loss_share_percent")),
                    number(row.get("formula_stored_max_abs_difference")),
                    "NO VERIFICABLE",
                ]
            )
    suffix += [
        table(
            [
                "Ventana",
                "Conjunto",
                "QLIKE original",
                "QLIKE MZ diagnóstico",
                "N orígenes",
                "Afines negativos",
                "Pisos activados",
                "% pérdida en piso",
                "Máx. diferencia fórmula/guardado",
                "Estado utilizable",
            ],
            mz_rows,
        ),
        "",
        "En confirmación B1 y B2 tienen respectivamente 9 y 11 pisos activados; aportan "
        "más del 99,98% de su pérdida MZ. La auditoría verificó las 25 sesiones sin "
        "ajustar modelos y sin demostrar fallo de suma, escala ni intercepto. "
        "[Prueba primaria](../../artifacts/rp4_v3_b4/mz_identity_receipt.json) · "
        "[Prueba de confirmación](../../artifacts/rp4_v3_secondary_mz_audit/REPORT.md) · "
        "[Recibo de confirmación](../../artifacts/rp4_v3_secondary_mz_audit/receipt.json). "
        "Se aplica el cierre NO VERIFICABLE autorizado para MZ, sin nueva recalibración.",
        "",
        "## Divulgación y custodia",
        "",
        "La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 "
        "con otra especificación. El PIT es proxy de tiempo fuente a 120 s, como en la literatura.",
        "",
        "Hueco UW aceptado: 2025-01-25 a 2025-02-24, sin relleno. Las versiones reutilizan "
        "ventanas y no son replicaciones independientes; un no rechazo no demuestra "
        "equivalencia a cero ni absorción. La reparación numérica no cambia las medias "
        "primarias ni demuestra por sí sola una ventaja global robusta.",
        "",
        f"Release de salto: `{evidence['release_sha256']}`. "
        f"Revisión 1: `{FROZEN_PINS['docs/rp4/results_v3_revision1.md']}`. "
        f"Auditoría MZ confirmación: `{mz_receipt_sha}`.",
        "",
        "[Recibo y comandos de esta revisión]"
        "(../../artifacts/rp4_v3_secondary_closeout/receipt.json) "
        "· [Pins y censo de cierre](../../artifacts/rp4_v3_secondary_closeout/evidence.json) "
        "· [Revisión anterior intacta](results_v3_revision1.md).",
        "",
        "RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false. Sin publicación, "
        "descargas ni modificación de resultados congelados.",
        "",
    ]
    encoded = prefix + original_block + ("\n".join(suffix)).encode()
    require(primary_block(encoded) == original_block, "PRIMARY_BYTES_CHANGED")
    return encoded


def execute(
    root: Path, private: Path, release_sha: str, receipt_shas: dict[str, str], command: str
) -> dict[str, Any]:
    destinations = [root / REPORT, root / FOLDER / "evidence.json", root / FOLDER / "receipt.json"]
    require(not any(p.exists() for p in destinations), "OUTPUT_ALREADY_EXISTS")
    started = datetime.now(UTC).isoformat()
    evidence = load_evidence(root, private, release_sha, receipt_shas)
    encoded = render(evidence)
    # Recheck every source pin before writing; no claim is based on a mutable snapshot.
    require(
        all(sha256(Path(p)) == digest for p, digest in evidence["pins"].items()),
        "INPUT_CHANGED_DURING_RENDER",
    )
    metadata = {
        "status": "COMPLETE_CLOSED_SECONDARY_PRESENTATION",
        "model_fits": 0,
        "new_inference_calculations": 0,
        "primary_rows": 8,
        "primary_block_sha256": hashlib.sha256(evidence["primary_block"]).hexdigest(),
        "primary_block_byte_preserved": True,
        "input_sha256": evidence["pins"],
        "release_sha256": release_sha,
        "addendum_sha256": ADDENDUM_SHA,
        "windows": {
            window: {
                "summary": bundle["summary"],
                "certificates": bundle["certificates"],
                "command": bundle["receipt"]["command"],
                "exit_code": 0,
                "log_sha256": bundle["receipt"]["log_sha256"],
                "receipt_sha256": receipt_shas[window],
            }
            for window, bundle in evidence["windows"].items()
        },
        "mz_status": "NO_VERIFICABLE_NO_ARITHMETICAL_BUG_DEMONSTRATED",
        "v4_changed": False,
        "frozen_artifacts_changed": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_bytes_once(destinations[0], encoded)
    write_json_once(destinations[1], metadata)
    result = {
        "status": "COMPLETE",
        "stage": "RP4_V3_B4_REVISION2_SECONDARY_CLOSEOUT",
        "exit_code": 0,
        "command": command,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "model_fits": 0,
        "new_inference_calculations": 0,
        "primary_block_byte_preserved": True,
        "producer_path": (FOLDER / "report_revision2.py").as_posix(),
        "producer_sha256": sha256(root / FOLDER / "report_revision2.py"),
        "test_sha256": sha256(root / FOLDER / "test_report_revision2.py"),
        "release_sha256": release_sha,
        "source_receipt_sha256": receipt_shas,
        "artifacts_sha256": {str(p): sha256(p) for p in destinations[:2]},
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_json_once(destinations[2], result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--primary-receipt-sha256", required=True)
    parser.add_argument("--confirmation-receipt-sha256", required=True)
    args = parser.parse_args()
    import psutil
    from threadpoolctl import threadpool_limits

    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    with threadpool_limits(limits=1):
        result = execute(
            ROOT.resolve(),
            PRIVATE.resolve(),
            args.release_sha256,
            {
                "primary": args.primary_receipt_sha256,
                "confirmation": args.confirmation_receipt_sha256,
            },
            "uv run --offline --frozen --no-sync python -B " + subprocess.list2cmdline(sys.argv),
        )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
