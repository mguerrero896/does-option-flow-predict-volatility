"""Two-pass v3 secondary presentation; original generator and results stay immutable.

Only closed, externally pinned summaries may reach this module's renderer. The
failed-only loader is implemented against the separate runner's final contract.
No fitting, numerical testing, AUC calculation or primary aggregation belongs here.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from artifacts.rp4_code.evaluate import sha256, write_bytes_once, write_json_once
from artifacts.rp4_v3_code import report_v3 as display
from artifacts.rp4_v3_secondary_closeout import report_revision2 as prior

NEWTON_ADDENDUM_SHA = "529067473ff602d47e0466426ce2af2e0f525d1ac5e42b4fd4230e38d17c52fa"
NEWTON_DOCUMENT_SHA = "7353209882a75316faf9f60da8d895739a5fb26e6f84bfb3cc01128c21d9f888"
FIRST_RELEASE_SHA = "7565795ddd4938f4c84068b2c2bb30c01905092150fb78c56aefa7626ca46bed"
PRIOR_PRODUCER_SHA = "e4d4d9ed795334f3c4128539fb6fd9ce614efac98e210729f945600c9f5889f2"
OUT = prior.PRIVATE / "newton_failed_only_v1"
LINEAGES = (
    "REUSED_ORIGINAL_V3",
    "REUSED_FIRST_REPAIR_SUCCESS",
    "NEWTON_FAILED_ONLY_ATTEMPT",
    "PRESERVED_INELIGIBLE_FAILURE",
)


def solver_audit(first: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    """Never assign an old failure's partial diagnostic to every lambda or phase."""
    before = (first.get("failure") or {}).get("diagnostics", {})
    rows = [
        {
            "session": first["session"],
            "model": first["model"],
            "phase": "primer fallo; fase no guardada; lambda=" + str(before.get("lambda")),
            "status": first["status"],
            "first_attempt_lbfgs_iterations": before.get("iterations"),
            "first_attempt_gradient": before.get("gradient_inf_norm_objective_over_n"),
            "certificate_status": "NO VERIFICABLE (intento preservado)",
        }
    ]
    if current["status"] == "COMPUTED":
        fit = current["fit"]
        solvers = [
            ("candidate lambda=" + str(row["lambda"]), row["solver"]) for row in fit["candidates"]
        ] + [("refit", fit["solver_refit"])]
    else:
        solvers = [
            ("nuevo fallo; fase no guardada", (current.get("failure") or {}).get("diagnostics", {}))
        ]
    for phase, diagnostic in solvers:
        newton = diagnostic.get("newton", {})
        rows.append(
            {
                "session": current["session"],
                "model": current["model"],
                "phase": phase,
                "status": current["status"],
                "new_call_lbfgs_iterations": diagnostic.get("lbfgs_iterations"),
                "newton_attempted_steps": newton.get("iterations"),
                "newton_accepted_steps": newton.get("accepted_steps"),
                "final_gradient": diagnostic.get("gradient_inf_norm_objective_over_n"),
                "certificate_status": "CERTIFIED"
                if current["status"] == "COMPUTED"
                and diagnostic.get("original_gradient_certificate_applicable") is True
                else "Excepción monoclase"
                if current["status"] == "COMPUTED"
                and diagnostic.get("original_gradient_certificate_applicable") is False
                else "NO VERIFICABLE",
            }
        )
    return rows


def validate_lineage(
    first: dict[str, Any],
    summary: dict[str, Any],
    fits: list[dict[str, Any]],
    manifest: list[dict[str, Any]],
    plan: dict[str, Any],
    release_sha: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # This pure predicate is from the hash-verified failed-only adapter, not a fit entrypoint.
    from artifacts.rp4_v3_secondary_repair.jump_newton_runner import eligible_failure

    old_fits = {(r["session"], r["model"]): r for r in first["fits"]}
    inventory = {(r["session"], r["model"]): r for r in plan["components"]}
    observed = {(r["session"], r["model"]): r for r in fits}
    references = {(r["session"], r["model"]): r for r in manifest}
    prior.require(
        len(inventory)
        == len(plan["components"])
        == len(observed)
        == len(fits)
        == len(references)
        == len(manifest)
        and set(inventory) == set(observed) == set(old_fits) == set(references),
        "NEWTON_COMPONENT_KEY_SET",
    )
    original_sources = {(r["session"], r["model"]): r for r in first["plan"]["components"]}
    normalized_manifest, audits = [], []
    for key, row in observed.items():
        old, source, reference = old_fits[key], inventory[key], references[key]
        eligible = eligible_failure(old)
        prior.require(
            source["eligible_newton"] is eligible and source["first_status"] == old["status"],
            "NEWTON_ELIGIBILITY_DRIFT",
        )
        prior.require(
            reference["first_component_sha256"] == source["first_component_sha256"]
            and reference["first_component_receipt_sha256"]
            == source["first_component_receipt_sha256"],
            "NEWTON_FIRST_COMPONENT_PIN",
        )
        if eligible:
            expected_lineage = "NEWTON_FAILED_ONLY_ATTEMPT"
        elif old["status"] == "COMPUTED":
            expected_lineage = (
                "REUSED_ORIGINAL_V3"
                if old["provenance"] == "REUSED_FROZEN_V3"
                else "REUSED_FIRST_REPAIR_SUCCESS"
            )
        else:
            expected_lineage = "PRESERVED_INELIGIBLE_FAILURE"
        prior.require(
            row["lineage"] == reference["lineage"] == expected_lineage, "NEWTON_LINEAGE_DRIFT"
        )
        prior.require(row["status"] == reference["status"], "NEWTON_REFERENCE_STATUS")
        if not eligible:
            prior.require(
                all(row[k] == old[k] for k in ("status", "fit", "failure", "provenance"))
                and reference["sha256"] == source["first_component_sha256"]
                and reference["component_receipt_sha256"]
                == source["first_component_receipt_sha256"]
                and row["new_attempt_elapsed_seconds"] == 0,
                "NEWTON_SUCCESS_OR_INELIGIBLE_CHANGED",
            )
        else:
            prior.require(
                row["model"].startswith("jump__log_ridge_harq__")
                and old["status"] == "NO VERIFICABLE",
                "NEWTON_UNAUTHORIZED_REFIT",
            )
            audits.extend(solver_audit(old, row))
        expected_outcome = (
            ("RECOVERED" if row["status"] == "COMPUTED" else "PERSISTENT_FAILURE")
            if eligible
            else ("PRESERVED_SUCCESS" if row["status"] == "COMPUTED" else "PERSISTENT_FAILURE")
        )
        prior.require(reference["outcome"] == expected_outcome, "NEWTON_OUTCOME_DRIFT")
        normalized_manifest.append(
            {
                **row,
                "original_component_sha256": original_sources[key]["component_sha256"]
                if key in original_sources
                else None,
            }
        )
    expected_counts = Counter((r["lineage"], r["status"]) for r in fits)
    recorded_counts = {(r["lineage"], r["status"]): r["N"] for r in summary["component_counts"]}
    prior.require(
        recorded_counts == dict(expected_counts)
        and len(recorded_counts) == len(summary["component_counts"]),
        "NEWTON_LINEAGE_CENSUS",
    )
    eligible_n = sum(r["eligible_newton"] for r in plan["components"])
    prior.require(
        eligible_n == plan["eligible_components"] == summary["eligible_newton_components"]
        and summary["successful_components_refitted"] == 0
        and summary["prior_attempts_preserved"] is True,
        "NEWTON_SCOPE_COUNTS",
    )
    normalized = copy.deepcopy(summary)
    by_provenance = Counter((r["provenance"], r["status"]) for r in fits)
    normalized["component_counts"] = [
        {"provenance": key[0], "status": key[1], "N": value}
        for key, value in sorted(by_provenance.items())
    ]
    # The existing common-mask, AUC-state and original-gradient guards apply unchanged.
    prior.validate_window(normalized, fits, normalized_manifest, first["plan"], release_sha)
    census = []
    for lineage in LINEAGES:
        for family in prior.FAMILIES:
            selected = [
                r for r in fits if r["lineage"] == lineage and f"__{family}__" in r["model"]
            ]
            census.append(
                {
                    "family": family,
                    "provenance": lineage,
                    "N_components": len(selected),
                    "computed": sum(r["status"] == "COMPUTED" for r in selected),
                    "failed": sum(r["status"] == "NO VERIFICABLE" for r in selected),
                }
            )
    return census, audits


def load_evidence(
    root: Path,
    first_root: Path,
    newton_root: Path,
    release_sha: str,
    first_receipt_shas: dict[str, str],
    newton_receipt_shas: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    pins: dict[str, str] = {}
    receipts = {}
    # Require both Newton closeouts BEFORE the old loader opens any first-pass AUC.
    for window in prior.WINDOWS:
        receipt = prior.verified(
            newton_root / "evaluation" / window / "receipt.json", newton_receipt_shas[window], pins
        )
        binding = {"release_sha256": release_sha, "window": window, "endpoint": "jump"}
        prior.require(
            receipt["status"] == "COMPLETE"
            and receipt["exit_code"] == 0
            and receipt["binding"] == binding,
            "NEWTON_WINDOW_NOT_CLOSED:" + window,
        )
        receipts[window] = receipt
    prior.verified(root / prior.FOLDER / "report_revision2.py", PRIOR_PRODUCER_SHA, pins)
    first = prior.load_evidence(root, first_root, FIRST_RELEASE_SHA, first_receipt_shas)
    pins.update(first["pins"])
    release = prior.verified(newton_root / "release.json", release_sha, pins)
    prior.require(
        release["first_release_sha256"] == FIRST_RELEASE_SHA
        and release["addendum_sha256"] == NEWTON_ADDENDUM_SHA
        and release["original_inventory_sha256"] == prior.INVENTORY_SHA
        and release["successful_components_refitted"] == 0
        and release["prior_attempts_preserved"] is True,
        "NEWTON_RELEASE_CONTRACT",
    )
    prior.verified(
        root / "artifacts/rp4_v3_secondary_newton_a1/addendum.json", NEWTON_ADDENDUM_SHA, pins
    )
    prior.verified(root / "docs/rp4/v3_secondary_newton_addendum_v1.md", NEWTON_DOCUMENT_SHA, pins)
    for relative, digest in {**release["code_sha256"], **release["test_sha256"]}.items():
        path = (root / relative).resolve()
        prior.require(path.is_relative_to(root), "NEWTON_CODE_PATH_ESCAPE")
        prior.verified(path, digest, pins)
    qa = prior.verified(newton_root / "qa_receipt.json", release["qa_receipt_sha256"], pins)
    prior.require(
        qa["status"] == "PASS"
        and qa["numeric_tests_executed"] is True
        and all(c["exit_code"] == 0 for c in qa["commands"]),
        "NEWTON_NUMERIC_QA",
    )
    inventory = prior.verified(newton_root / "inventory.json", release["inventory_sha256"], pins)
    prior.require(
        inventory["first_release_sha256"] == FIRST_RELEASE_SHA, "NEWTON_INVENTORY_RELEASE"
    )
    windows = {}
    for window in prior.WINDOWS:
        output = newton_root / "evaluation" / window
        receipt = receipts[window]
        binding = {"release_sha256": release_sha, "window": window, "endpoint": "jump"}
        prior.require(receipt["code_sha256"] == release["code_sha256"], "NEWTON_RECEIPT_CODE")
        names = (
            "summary.json",
            "fit_diagnostics.json",
            "component_manifest.json",
            "summary_receipt.json",
        )
        hashes = {Path(p).resolve(): h for p, h in receipt["artifacts_sha256"].items()}
        prior.require(
            set(hashes) == {(output / name).resolve() for name in names},
            "NEWTON_RECEIPT_ARTIFACT_SET",
        )
        values = {path.name: prior.verified(path, digest, pins) for path, digest in hashes.items()}
        log = Path(receipt["log"]).resolve()
        prior.require(log.is_relative_to(newton_root), "NEWTON_LOG_PATH")
        prior.verified(log, receipt["log_sha256"], pins)
        child = values["summary_receipt.json"]
        prior.require(
            child["binding"] == binding
            and set(child["artifacts_sha256"]) == set(names[:3])
            and all(
                child["artifacts_sha256"][name] == hashes[(output / name).resolve()]
                for name in names[:3]
            ),
            "NEWTON_SUMMARY_RECEIPT",
        )
        plan = next(p for p in inventory["windows"] if p["window"] == window)
        prior.require(
            plan["first_receipt_sha256"] == first_receipt_shas[window], "NEWTON_FIRST_RECEIPT"
        )
        fits, manifest = values["fit_diagnostics.json"], values["component_manifest.json"]
        summary = values["summary.json"]
        census, audits = validate_lineage(
            first["windows"][window], summary, fits, manifest, plan, release_sha
        )
        planned = {(r["session"], r["model"]): r for r in plan["components"]}
        for reference in manifest:
            path = Path(reference["path"]).resolve()
            scope = (
                output
                if reference["lineage"] == "NEWTON_FAILED_ONLY_ATTEMPT"
                else (first_root / "evaluation" / window)
            )
            expected = scope / "components" / reference["session"] / (reference["model"] + ".json")
            prior.require(
                path == expected.resolve() and sha256(path) == reference["sha256"],
                "NEWTON_COMPONENT_PHYSICAL_HASH",
            )
            component_receipt = scope / "component_receipts" / reference["session"] / path.name
            prior.require(
                sha256(component_receipt) == reference["component_receipt_sha256"],
                "NEWTON_COMPONENT_RECEIPT_HASH",
            )
            first_path = (
                first_root / "evaluation" / window / "components" / reference["session"] / path.name
            )
            prior.require(
                sha256(first_path)
                == planned[(reference["session"], reference["model"])]["first_component_sha256"],
                "NEWTON_ORIGINAL_COMPONENT_CHANGED",
            )
        for name, digest in summary["session_sha256"].items():
            prior.require(
                Path(name).name == name and sha256(output / "sessions" / name) == digest,
                "NEWTON_SESSION_HASH",
            )
        for session, digest in plan["first_session_sha256"].items():
            prior.require(
                sha256(first_root / "evaluation" / window / "sessions" / (session + ".json"))
                == digest,
                "NEWTON_FIRST_SESSION_HASH",
            )
        windows[window] = {
            "summary": summary,
            "receipt": receipt,
            "provenance_rows": census,
            "solver_audit": audits,
        }
    first_end = max(
        datetime.fromisoformat(b["receipt"]["completed_at_utc"]) for b in first["windows"].values()
    )
    prior.require(
        first_end <= min(datetime.fromisoformat(r["started_at_utc"]) for r in receipts.values())
        and datetime.fromisoformat(receipts["primary"]["completed_at_utc"])
        <= datetime.fromisoformat(receipts["confirmation"]["started_at_utc"]),
        "NEWTON_RESOURCE_OVERLAP",
    )
    return first, {"release_sha256": release_sha, "windows": windows, "pins": pins}


def final_auc_section(windows: dict[str, dict[str, Any]]) -> str:
    """Render exact saved _jump output, without recalculating any estimator."""
    auc_rows, delta_rows, census_rows = [], [], []
    excluded_rows: list[list[str]] = []
    for window, label in prior.WINDOWS.items():
        jump = windows[window]["summary"]["jump_secondary"]
        excluded_rows.extend(
            [label, row["session"], row["reason"]] for row in jump["excluded_sessions"]
        )
        for family in jump["families"]:
            for name in prior.SETS:
                row = family["auc"][name]
                auc_rows.append(
                    [
                        label,
                        display.family_label(family["family"], "jump"),
                        name,
                        display.number(row.get("estimate")),
                        prior.interval(row),
                        prior.count(family.get("N_sessions")),
                        prior.count(family.get("N_origins")),
                        prior.count(family.get("invalid_class_resamples")),
                        row["status"],
                        row.get("reason", "—"),
                    ]
                )
        for row in jump["contrasts"]:
            delta_rows.append(
                [
                    label,
                    display.family_label(row["family"], "jump"),
                    row["contrast"].replace("_over_", "/"),
                    display.number(row.get("estimate"), signed=True),
                    prior.interval(row),
                    display.number(row.get("p_raw")),
                    display.number(row.get("p_for_decision")),
                    prior.sequence_text(row),
                    prior.count(row.get("N_sessions")),
                    prior.count(row.get("N_origins")),
                ]
            )
        census_rows.append(
            [
                label,
                prior.count(jump.get("N_sessions")),
                prior.count(jump.get("N_origins")),
                prior.count(jump.get("positive_labels")),
                prior.count(jump.get("negative_labels")),
                str(len(jump["excluded_sessions"])),
            ]
        )
    return "\n".join(
        [
            "## Salto: resultado final combinado tras la resolución numérica",
            "",
            "Estas tablas usan los componentes completos del primer pase sin cambiarlos y "
            "las salidas del pase Newton exclusivamente para los fallos que eran elegibles. "
            "La AUC es la salida guardada del mismo agregador secundario v3: 9.999 remuestreos "
            "por bloques de sesión y secuencia unilateral H1 → H2 por familia. No se elige "
            "entre los dos pases por su AUC. Los valores del primer pase se conservan a "
            "continuación como registro de ejecución, no como otra réplica independiente.",
            "",
            display.table(
                [
                    "Ventana",
                    "Familia",
                    "Conjunto",
                    "AUC final",
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
            display.table(
                [
                    "Ventana",
                    "Familia",
                    "Contraste",
                    "Delta AUC final",
                    "IC95%",
                    "p crudo unilateral",
                    "p de decisión secuencial",
                    "Decisión secundaria",
                    "N sesiones",
                    "N orígenes",
                ],
                delta_rows,
            ),
            "",
            display.table(
                [
                    "Ventana",
                    "N sesiones final",
                    "N orígenes final",
                    "Etiquetas positivas",
                    "Etiquetas negativas",
                    "Sesiones aún excluidas del salto",
                ],
                census_rows,
            ),
            "",
            (
                display.table(
                    ["Ventana", "Sesión aún excluida", "Motivo final guardado"], excluded_rows
                )
                if excluded_rows
                else "Cero sesiones excluidas del salto final, según los dos agregados cerrados."
            ),
            "",
            "Los IC/p ausentes siguen NO VERIFICABLES; nunca se convierten en cero. Una "
            "H2 no abierta conserva su p nominal como diagnóstico, sin decisión secuencial.",
            "",
        ]
    )


def newton_execution_section(evidence: dict[str, Any]) -> str:
    """Only normalized, validated metadata is summarized in these resource tables."""
    component_rows, gradient_rows, resource_rows = [], [], []
    for window, label in prior.WINDOWS.items():
        bundle = evidence["windows"][window]
        for row in bundle["provenance_rows"]:
            component_rows.append(
                [
                    label,
                    display.family_label(row["family"], "jump"),
                    row["provenance"],
                    prior.count(row.get("N_components")),
                    prior.count(row.get("computed")),
                    prior.count(row.get("failed")),
                ]
            )
        for row in bundle["solver_audit"]:
            gradient_rows.append(
                [
                    label,
                    row["session"],
                    row["model"],
                    row["phase"],
                    row["status"],
                    prior.count(row.get("first_attempt_lbfgs_iterations")),
                    prior.count(row.get("new_call_lbfgs_iterations")),
                    prior.count(row.get("newton_attempted_steps")),
                    prior.count(row.get("newton_accepted_steps")),
                    display.number(row.get("first_attempt_gradient")),
                    display.number(row.get("final_gradient")),
                    row.get("certificate_status", "NO VERIFICABLE"),
                ]
            )
        receipt, resources = bundle["receipt"], bundle["summary"]["resources"]
        resource_rows.append(
            [
                label,
                prior.count(resources.get("threads_total_max")),
                str(resources.get("priority")),
                prior.count(receipt.get("exit_code")),
                display.number(receipt.get("elapsed_seconds")),
                str(receipt.get("started_at_utc", "NO VERIFICABLE")),
                str(receipt.get("completed_at_utc", "NO VERIFICABLE")),
            ]
        )
    return "\n".join(
        [
            "## Segundo pase: Newton sólo para fallos elegibles",
            "",
            "El [addendum Newton](v3_secondary_newton_addendum_v1.md) quedó registrado antes "
            "de consultar AUC y antes de ejecutar esta resolución: "
            f"JSON `{NEWTON_ADDENDUM_SHA}`; documento `{NEWTON_DOCUMENT_SHA}`. "
            "El rechazo inicial de B2 lineal del 2025-03-26 se conserva: gradiente "
            "1.0226994386690321e-8 frente al certificado 1e-8. Su fallo fue correcto bajo "
            "el umbral registrado; no se reclasifica como éxito del primer pase.",
            "",
            "La resolución mantiene objetivo, cinco lambdas, validación temporal, datos y "
            "umbral. Después de las mismas fases L-BFGS permite hasta ocho pasos Newton, "
            "sin jitter, con descenso certificado y la excepción de un ULP descrita en el "
            "addendum. Los componentes COMPUTED no se vuelven a ajustar, ni se vuelve a "
            "ajustar LightGBM. Cada llamada nueva y su pulido se cuentan aparte: reconstruir "
            "un coeficiente fallido que no estaba guardado no equivale a reutilizarlo.",
            "",
            display.table(
                [
                    "Ventana",
                    "Familia",
                    "Procedencia final",
                    "Componentes",
                    "COMPUTED",
                    "NO VERIFICABLE",
                ],
                component_rows,
            ),
            "",
            display.table(
                [
                    "Ventana",
                    "Sesión",
                    "Componente",
                    "Fase",
                    "Estado",
                    "Iteraciones L-BFGS intento anterior",
                    "Iteraciones L-BFGS nueva llamada",
                    "Pasos Newton intentados",
                    "Pasos Newton aceptados",
                    "Gradiente previo",
                    "Gradiente final",
                    "Certificado final",
                ],
                gradient_rows,
            )
            if gradient_rows
            else "No hubo llamadas Newton elegibles, comprobado contra el inventario cerrado.",
            "",
            "La tabla conserva sólo diagnósticos guardados. Un gradiente o coste anterior "
            "no registrado figura como NO VERIFICABLE, no como cero; el primer fallo puede "
            "documentar una sola lambda y no todo el trabajo de la llamada.",
            "",
            display.table(
                [
                    "Ventana",
                    "Máximo hilos de cálculo",
                    "Prioridad Windows",
                    "Código de salida",
                    "Segundos segundo pase",
                    "Inicio UTC",
                    "Fin UTC",
                ],
                resource_rows,
            ),
            "",
            "Se verificó que ambos cierres del primer pase preceden al inicio de Newton; "
            "no hubo ejecutores secundarios simultáneos. Los recursos del primer pase "
            "están en su propia tabla y no se eliminan del coste total. MZ, media primaria, "
            "cuantil y v4 permanecen intactos.",
            "",
            f"Release Newton: `{evidence['release_sha256']}`. "
            f"Release del primer pase: `{FIRST_RELEASE_SHA}`.",
            "",
        ]
    )


def replace_once(text: str, old: str, new: str) -> str:
    prior.require(text.count(old) == 1, "NEWTON_REPORT_ANCHOR_DRIFT")
    return text.replace(old, new, 1)


def render(first: dict[str, Any], newton: dict[str, Any]) -> bytes:
    """Adapt presentation only; use the prior immutable producer for original sections."""
    baseline = prior.render(first).decode("utf-8")
    text = replace_once(
        baseline,
        "## Salto: AUC fuera de muestra y contrastes secundarios",
        final_auc_section(newton["windows"])
        + "\n## Primer pase de salto: resultados preservados antes de Newton",
    )
    text = replace_once(
        text, "## Alcance de la reparación y convergencia", "## Primer pase: alcance y convergencia"
    )
    text = replace_once(
        text,
        "### Fallos de componentes y recursos",
        "### Primer pase: fallos de componentes y recursos",
    )
    text = replace_once(
        text,
        "## MZ: NO VERIFICABLE como recalibración utilizable",
        newton_execution_section(newton) + "\n## MZ: NO VERIFICABLE como recalibración utilizable",
    )
    text = replace_once(
        text,
        "Esta revisión cierra los intentos secundarios de salto de ambas ventanas.",
        "Esta revisión documenta los dos pases secundarios de salto y su resultado final "
        "combinado; conserva también íntegra la evidencia del primer pase.",
    )
    result = text.encode("utf-8")
    prior.require(prior.primary_block(result) == first["primary_block"], "NEWTON_PRIMARY_CHANGED")
    return result


def execute(
    root: Path,
    first_root: Path,
    newton_root: Path,
    release_sha: str,
    first_receipt_shas: dict[str, str],
    newton_receipt_shas: dict[str, str],
    command: str,
) -> dict[str, Any]:
    paths = (
        root / prior.REPORT,
        root / prior.FOLDER / "evidence.json",
        root / prior.FOLDER / "receipt.json",
    )
    prior.require(not any(path.exists() for path in paths), "NEWTON_OUTPUT_ALREADY_EXISTS")
    started = datetime.now(UTC).isoformat()
    first, final = load_evidence(
        root, first_root, newton_root, release_sha, first_receipt_shas, newton_receipt_shas
    )
    encoded = render(first, final)
    prior.require(
        all(sha256(Path(path)) == digest for path, digest in final["pins"].items()),
        "NEWTON_SOURCE_CHANGED_DURING_RENDER",
    )
    metadata = {
        "status": "COMPLETE_TWO_PASS_SECONDARY_PRESENTATION",
        "model_fits": 0,
        "new_inference_calculations": 0,
        "primary_rows": 8,
        "primary_block_byte_preserved": True,
        "primary_block_sha256": hashlib.sha256(first["primary_block"]).hexdigest(),
        "first_release_sha256": FIRST_RELEASE_SHA,
        "newton_release_sha256": release_sha,
        "newton_addendum_sha256": NEWTON_ADDENDUM_SHA,
        "input_sha256": final["pins"],
        "first_pass": {
            window: {
                "summary": bundle["summary"],
                "certificates": bundle["certificates"],
                "receipt": bundle["receipt"],
            }
            for window, bundle in first["windows"].items()
        },
        "newton_final": final["windows"],
        "mz_status": "NO_VERIFICABLE_NO_ARITHMETICAL_BUG_DEMONSTRATED",
        "prior_primary_changed": False,
        "v4_changed": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_bytes_once(paths[0], encoded)
    write_json_once(paths[1], metadata)
    receipt = {
        "status": "COMPLETE",
        "stage": "RP4_V3_B4_REVISION2_TWO_PASS_CLOSEOUT",
        "exit_code": 0,
        "command": command,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "model_fits": 0,
        "new_inference_calculations": 0,
        "primary_block_byte_preserved": True,
        "first_release_sha256": FIRST_RELEASE_SHA,
        "newton_release_sha256": release_sha,
        "source_receipt_sha256": {"first": first_receipt_shas, "newton": newton_receipt_shas},
        "producer_path": (prior.FOLDER / "report_newton_revision2.py").as_posix(),
        "producer_sha256": sha256(root / prior.FOLDER / "report_newton_revision2.py"),
        "test_sha256": sha256(root / prior.FOLDER / "test_report_newton_revision2.py"),
        "prior_generator_sha256": PRIOR_PRODUCER_SHA,
        "artifacts_sha256": {str(path): sha256(path) for path in paths[:2]},
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_json_once(paths[2], receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--newton-release-sha256", required=True)
    for stage in ("first", "newton"):
        for window in prior.WINDOWS:
            parser.add_argument(f"--{stage}-{window}-receipt-sha256", required=True)
    args = parser.parse_args()
    import psutil
    from threadpoolctl import threadpool_limits

    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    receipt_pins = {
        stage: {
            window: getattr(args, f"{stage}_{window}_receipt_sha256") for window in prior.WINDOWS
        }
        for stage in ("first", "newton")
    }
    with threadpool_limits(limits=1):
        result = execute(
            prior.ROOT.resolve(),
            prior.PRIVATE.resolve(),
            OUT.resolve(),
            args.newton_release_sha256,
            receipt_pins["first"],
            receipt_pins["newton"],
            "uv run --offline --frozen --no-sync python -B " + subprocess.list2cmdline(sys.argv),
        )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
