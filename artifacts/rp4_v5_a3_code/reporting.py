"""A3 RV15-only five-family reports; frozen A1/A2 sources remain unchanged."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from artifacts.rp4_v5_a2_code import reporting as a2

from mds650.metrics import holm_adjust

a1 = a2.a1
BASE_FAMILIES = tuple(family for family in a2.BASE_FAMILIES if family != "mlp_log")
SELECTORS = a2.SELECTORS
FAMILIES = (*BASE_FAMILIES, *SELECTORS)
SETS = a2.SETS
HORIZONS = (15,)
N_CALENDAR = a2.N_CALENDAR
DEFERRED = "DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN"


def _validate(
    records: Any, expected_sessions: Sequence[str] | None = None
) -> list[Mapping[str, Any]]:
    rows = a2._validate(records, expected_sessions)
    if any(row["family"] not in BASE_FAMILIES or row["horizon_minutes"] != 15 for row in rows):
        raise ValueError("A3_REPORT_ONLY_RV15_FIVE_REGISTERED_FAMILIES")
    return rows


def summarize_family(
    records: Any, *, expected_sessions: Sequence[str] | None = None
) -> pd.DataFrame:
    return a2.summarize_family(
        _validate(records, expected_sessions), expected_sessions=expected_sessions
    )


def assemble_sessions(records: Any) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in _validate(records):
        grouped[row["session"]][row["family"]] = row
    assembled = []
    for session, families in sorted(grouped.items()):
        if set(families) != set(BASE_FAMILIES):
            raise ValueError("A3_REPORT_FIVE_FAMILY_CANDIDATES_REQUIRED")
        reference = families[BASE_FAMILIES[0]]
        forecasts = {family: dict(families[family]["forecasts"]) for family in BASE_FAMILIES}
        fits, selection = {}, {}
        for name in SETS:
            fits[name] = {family: families[family]["fits"][name] for family in BASE_FAMILIES}
            scores = {
                family: fits[name][family]["selected"]["validation_qlike"]
                for family in BASE_FAMILIES
            }
            ranking = sorted(
                BASE_FAMILIES, key=lambda family: (scores[family], BASE_FAMILIES.index(family))
            )
            selection[name] = {
                "primary": ranking[0],
                "top2": ranking[:2],
                "validation_qlike": scores,
            }
            forecasts.setdefault(SELECTORS[0], {})[name] = list(forecasts[ranking[0]][name])
            forecasts.setdefault(SELECTORS[1], {})[name] = (
                (np.asarray(forecasts[ranking[0]][name]) + forecasts[ranking[1]][name]) / 2
            ).tolist()
        assembled.append(
            {
                "session": session,
                "horizon_minutes": 15,
                "binding": {**reference["binding"], "window": "development", "horizon_minutes": 15},
                "keys": reference["keys"],
                "target": reference["target"],
                "forecasts": forecasts,
                "selection": selection,
                "fits": fits,
            }
        )
    return assembled


def progress(records: Any, expected_sessions: Sequence[str]) -> pd.DataFrame:
    full = a2.progress(_validate(records, expected_sessions), expected_sessions)
    return full[full["horizon_minutes"].eq(15) & full["family"].isin(BASE_FAMILIES)].reset_index(
        drop=True
    )


def progress_line(frame: pd.DataFrame) -> str:
    return "RV15: " + ", ".join(
        f"{row.family} {row.N_sessions}/{row.N_calendar}" for row in frame.itertuples()
    )


def inference_horizon(
    losses: pd.DataFrame, expected_sessions: Sequence[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Identical A2 estimator and decisions, with the newly registered five-family census."""
    calendar = a2._calendar(expected_sessions)
    if (
        losses.empty
        or not set(a2.LOSS_COLUMNS) <= set(losses)
        or set(losses["horizon_minutes"]) != {15}
        or set(losses["family"]) != set(FAMILIES)
    ):
        raise ValueError("A3_REPORT_INFERENCE_REQUIRES_FIVE_FAMILIES_AND_TWO_SELECTORS")
    pivots = {}
    for family in FAMILIES:
        subset = losses[losses["family"].eq(family)]
        if subset.duplicated(["session_date", "information_set"]).any():
            raise ValueError("A3_REPORT_DUPLICATE_LOSS")
        pivot = subset.pivot(
            index="session_date", columns="information_set", values="qlike"
        ).sort_index()
        if (
            tuple(pivot.index) != calendar
            or set(pivot.columns) != set(SETS)
            or not np.isfinite(pivot.to_numpy(dtype=float)).all()
        ):
            raise ValueError("A3_REPORT_INFERENCE_REQUIRES_EXACT_419_COMPLETE_SESSIONS")
        pivots[family] = pivot
    contrasts, chains = [], {}
    for selector in SELECTORS:
        pivot = pivots[selector]
        opened, rows = True, []
        for contrast, base, expanded in a1.inf.CONTRASTS:
            result = a1.inf.session_contrast(
                (pivot[base] - pivot[expanded]).to_numpy(), **a1.INFERENCE
            )
            available = a1._available(result)
            reject = bool(
                opened and available and result["estimate"] > 0 and result["p_raw"] <= 0.05
            )
            row = {
                **result,
                "horizon_minutes": 15,
                "family": selector,
                "contrast": contrast,
                "inference_role": "PRIMARY",
                "baseline_qlike": float(pivot[base].mean()),
                "expanded_qlike": float(pivot[expanded].mean()),
                "p_nominal": result["p_raw"],
                "p_bonferroni5": min(1.0, 5.0 * result["p_raw"]) if available else None,
                "p_for_decision": result["p_raw"] if opened and available else None,
                "hypothesis_status": "NOT_TESTED"
                if not opened
                else "NO_VERIFICABLE"
                if not available
                else "REJECTED"
                if reject
                else "NOT_REJECTED",
                "rejected": reject,
            }
            denominator = row["baseline_qlike"]
            row["qlike_reduction_percent"] = (
                100 * result["estimate"] / denominator if available and denominator > 0 else None
            )
            contrasts.append(row)
            rows.append(row)
            opened = reject
        available = all(a1._available(row) for row in rows)
        chains[selector] = {
            "horizon_minutes": 15,
            "family": selector,
            "inference_role": "PRIMARY",
            "q_chain": max(row["p_raw"] for row in rows) if available else None,
            "both_positive": available and all(row["estimate"] > 0 for row in rows),
            "both_nominal_gates_rejected": opened,
            "holm_unavailable_treated_as_one": not available,
        }
    adjusted = holm_adjust(
        {
            selector: chain["q_chain"] if chain["q_chain"] is not None else 1.0
            for selector, chain in chains.items()
        }
    )
    for selector, chain in chains.items():
        value = adjusted[selector] if chain["q_chain"] is not None else None
        chain.update(
            p_holm_chain=value,
            p_holm_chain_bonferroni5=min(1.0, 5.0 * value) if value is not None else None,
            chain_holm_rejected=bool(
                chain["both_positive"] and value is not None and value <= 0.05
            ),
            holm_family_size=2,
        )
    return contrasts, list(chains.values())


def _comparison(comparison: pd.DataFrame | None) -> pd.DataFrame:
    if comparison is None:
        return pd.DataFrame()
    # The runner supplies the existing, verified 18-row comparison CSV.
    return (
        a2._comparison(comparison).loc[comparison["horizon_minutes"].eq(15)].reset_index(drop=True)
    )


def _frequencies(sessions: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    rows = []
    for name in SETS:
        if sessions:
            for family in BASE_FAMILIES:
                count = sum(row["selection"][name]["primary"] == family for row in sessions)
                top2 = sum(family in row["selection"][name]["top2"] for row in sessions)
                rows.append(
                    {
                        "horizon_minutes": 15,
                        "information_set": name,
                        "family": family,
                        "selected_sessions": count,
                        "N_sessions": len(sessions),
                        "selection_frequency": count / len(sessions),
                        "top2_sessions": top2,
                        "mean_top2_weight": 0.5 * top2 / len(sessions),
                        "status": "COMPLETE",
                    }
                )
        rows.append(
            {
                "horizon_minutes": 15,
                "information_set": name,
                "family": "mlp_log",
                "selected_sessions": None,
                "N_sessions": 0,
                "selection_frequency": None,
                "top2_sessions": None,
                "mean_top2_weight": None,
                "status": DEFERRED,
            }
        )
    return pd.DataFrame(rows)


def build_snapshot(
    records: Any,
    spec: Mapping[str, Any],
    expected_sessions: Sequence[str],
    comparison: pd.DataFrame | None = None,
    gpu_control: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    calendar = a2._calendar(expected_sessions)
    a2._inference_spec(spec)
    rows = _validate(records, calendar)
    if any(key["asset"] not in spec["assets"] for row in rows for key in row["keys"]):
        raise ValueError("A3_REPORT_ASSET_SPECIFICATION_DRIFT")
    counts = progress(rows, calendar)
    complete = bool(counts["N_sessions"].eq(N_CALENDAR).all())
    assembled = assemble_sessions(rows) if complete else []
    raw = [
        loss for row in rows for loss in a2._session_losses(row, {row["family"]: row["forecasts"]})
    ]
    raw.extend(
        loss
        for row in assembled
        for loss in a2._session_losses(
            row, {family: row["forecasts"][family] for family in SELECTORS}
        )
    )
    losses = pd.DataFrame(raw, columns=a2.LOSS_COLUMNS)
    table = a2._table(losses, calendar_verified=True)
    deferred = pd.DataFrame(
        [
            {
                "version": "v5",
                "horizon_minutes": 15,
                "family": "mlp_log",
                "information_set": name,
                "qlike": np.nan,
                "mae": np.nan,
                "rmse": np.nan,
                "N_sessions": 0,
                "N_origins": 0,
                "N_asset_sessions": 0,
                "N_calendar": N_CALENDAR,
                "status": DEFERRED,
            }
            for name in SETS
        ]
    )
    table = pd.concat([table, deferred], ignore_index=True)
    contrasts, chains = inference_horizon(losses, calendar) if complete else ([], [])
    candidate_frequencies, exclusions = a2._candidate_tables(rows)
    comparator = _comparison(comparison)
    summary = {
        "schema_version": "rp4-v5-a3-snapshot-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "COMPLETE" if complete else "PARTIAL",
        "scope": "A3_RV15_ONLY_FIVE_FAMILIES_DEVELOPMENT",
        "N_calendar": N_CALENDAR,
        "expected_sessions": list(calendar),
        "calendar_sha256": a2._digest(list(calendar)),
        "N_family_records": len(rows),
        "input_records_sha256": a2._digest(rows),
        "binding": dict(rows[0]["binding"]) if rows else None,
        "registered_horizons": [15],
        "completed_horizons": [15] if complete else [],
        "deferred_horizons": [5, 30],
        "registered_base_families": list(BASE_FAMILIES),
        "deferred_families": {"mlp_log": DEFERRED},
        "selector_inference_available_horizons": [15] if complete else [],
        "all_horizons_complete": complete,
        "inference_parameters": a1.INFERENCE.copy(),
        "contrasts": contrasts,
        "selector_chains": chains,
        "decision": a2._decision(contrasts, chains),
        "candidate_exclusion_events": len(exclusions),
        "comparison_sha256": hashlib.sha256(comparator.to_csv(index=False).encode()).hexdigest(),
        "amendment": spec.get("amendment", {}),
        "environment": spec.get("environment", {}),
        "gpu_control": dict(gpu_control)
        if gpu_control is not None
        else {
            "status": "NOT_APPLICABLE_A3_CPU_ONLY",
            "prior_gpu_measurement": "A2 memory probe",
        },
        "progress_line": progress_line(counts),
        "interval_scope": "pointwise two-sided percentile 95%; no simultaneous coverage claim",
        "multiplicity_scope": (
            "Fifth historical reading with disclosed cost amendments; Holm of two chain maxima "
            "and times five declared version bound, not adaptive-search correction."
        ),
        "secondary_can_rescue_primary": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
        "disclaimer": "NOT INVESTMENT ADVICE",
    }
    snapshot = {
        "summary": summary,
        "table": table,
        "losses": losses,
        "frequencies": _frequencies(assembled),
        "candidate_frequencies": candidate_frequencies,
        "exclusions": exclusions,
        "progress": counts,
        "comparison": comparator,
    }
    snapshot["markdown"] = _markdown(snapshot)
    return snapshot


def _markdown(snapshot: Mapping[str, Any]) -> str:
    summary = snapshot["summary"]
    contrasts = pd.DataFrame(summary["contrasts"]).reindex(
        columns=[
            "family",
            "contrast",
            "estimate",
            "ci_low",
            "ci_high",
            "p_nominal",
            "p_for_decision",
            "p_bonferroni5",
            "hypothesis_status",
        ]
    )
    chains = pd.DataFrame(summary["selector_chains"]).reindex(
        columns=[
            "family",
            "q_chain",
            "p_holm_chain",
            "p_holm_chain_bonferroni5",
            "chain_holm_rejected",
        ]
    )
    environment = pd.DataFrame(
        [
            {"campo": key, "valor": a2._json(value).decode().strip()}
            for key, value in summary["environment"].items()
        ]
    )
    parts = [
        "# RP4 v5 — intento A3, enmienda técnica 2",
        f"Estado: **{summary['status']}**. "
        f"Actualizado: {summary['created_at_utc']}. RV15 solamente.",
        "RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.",
        "## Cobertura y progreso",
        "Calendario exacto de 419 sesiones del preflight A1. Se mantienen las mismas claves, "
        "objetivos y conjuntos B0/B1/B2. PARTIAL contiene sólo sesiones terminadas; las familias "
        "pueden cubrir fechas distintas y no se declara un ganador con esa muestra incompleta.",
        a1._markdown(snapshot["progress"]),
        "## Métricas por familia y conjunto",
        "QLIKE y MAE promedian orígenes dentro de activo/sesión y dan igual peso a activos y "
        "sesiones. RMSE aplica la raíz después de promediar el error cuadrático.",
        a1._markdown(snapshot["table"]),
        "MLP: diferida por coste, no evaluada en esta corrida A3. Su estado es "
        + DEFERRED
        + "; no se imputan pérdidas ni frecuencias de selección. "
        "A1 sí ajustó la red en un componente parcial y A2 la ajustó en la sesión de prueba "
        "de memoria/GPU. No se afirma que nunca se evaluó. RV5 y RV30 quedan diferidos.",
        "## Referencia histórica v4, RV15",
        a1._markdown(snapshot["comparison"]),
        "Los comparadores conservan las 419 sesiones. Una tabla PARTIAL no constituye una "
        "comparación pareada contra ellos. v4 conserva el titular; no hay prueba directa v5/v4.",
        "## Selector e inferencia",
        "El selector y el conjunto top2 usan las cinco familias: persistencia, HAR, ridge, "
        "Elastic Net y LightGBM. Se eligen exclusivamente por QLIKE de validación temporal, "
        "con desempate en ese orden; top2 promedia niveles con pesos 0,5/0,5. Sólo se calculan "
        "cuando las cinco familias completan las 419 sesiones.",
        a1._markdown(contrasts),
        a1._markdown(chains),
        "Se mantiene H1→H2: H2 sólo se abre tras rechazar H1 positivamente al 5%. Su p nominal "
        "se divulga aun cerrada la puerta. Cada cadena usa max(pH1,pH2), Holm entre los dos "
        "selectores y Bonferroni ×5 como cota declarada entre versiones. Bootstrap de sesiones: "
        "bloque 5, 9.999 repeticiones, semilla 20260908; "
        "intervalos puntuales bilaterales del 95%. "
        "Las enmiendas de coste son lecturas históricas divulgadas; ×5 no corrige toda la "
        "búsqueda adaptativa ni convierte estos resultados en confirmación prospectiva.",
        "Regla nominal RV15 B2/B1 del selector: " + summary["decision"]["nominal_status"] + ". "
        "Requiere delta positivo, p unilateral <0,05 e intervalo 95% que excluya cero. "
        "Se reporta separadamente del resultado de H1 y Holm.",
        "## Frecuencias del selector y familia diferida",
        a1._markdown(snapshot["frequencies"]),
        "## Elastic Net: candidatos y exclusiones por etapa",
        a1._markdown(snapshot["candidate_frequencies"]),
        "### Exclusiones por sesión",
        a1._markdown(snapshot["exclusions"]),
        "## Coste, entorno y custodia",
        "[Enmienda técnica 2](specification_v5_technical_amendment_2.md). "
        "LightGBM vuelve al productor CPU congelado rp4_v2_code.models.fit_lightgbm, con hojas "
        "[15,31,63], semilla 20260908 y deterministic=True. A3 no ajusta MLP ni usa GPU.",
        "La Parte 18 comunicó aproximadamente 193 segundos por sesión "
        "para LightGBM GPU en A2 y extrapolaciones RV15 de 22,49 h "
        "para LightGBM GPU y 28,22 h para MLP GPU. "
        "Son mediciones/extrapolaciones de A2, no tiempos A3 observados; motivaron el recorte. "
        "La instrucción posterior fija margen de memoria del 15%: "
        "se utiliza 0,85 de la memoria "
        "asignable para calcular fragmentos con el pico nuevo medido.",
        a1._markdown(environment),
        "Los intentos A1/A2, sus sellos, pruebas y recibos quedan conservados. La ejecución A3 "
        "es independiente del chat, conserva recibos por sesión y actualiza progress.json "
        "al menos cada cinco minutos. Cada publicación guarda snapshot y recibo inmutables.",
        "Binding: " + a2._json(summary["binding"]).decode().strip(),
        "Calendario SHA256: " + summary["calendar_sha256"] + ". "
        "Registros SHA256: " + summary["input_records_sha256"] + ".",
    ]
    return "\n\n".join(parts) + "\n"


def write_snapshot(
    snapshot: Mapping[str, Any], snapshot_dir: Path, output: Path, *, update_id: str
) -> dict[str, Any]:
    """Same A2 artifact contract with an explicit A3 receipt schema."""
    if not isinstance(update_id, str) or not update_id:
        raise ValueError("A3_REPORT_UPDATE_ID_REQUIRED")
    destination, output = Path(snapshot_dir), Path(output)
    payloads = {
        "summary.json": a2._json(snapshot["summary"]),
        "results_v5.md": snapshot["markdown"].encode(),
        **{
            f"{name}.csv": snapshot[name].to_csv(index=False, lineterminator="\n").encode()
            for name in (
                "table",
                "losses",
                "frequencies",
                "candidate_frequencies",
                "exclusions",
                "progress",
                "comparison",
            )
        },
    }
    receipt = {
        "schema_version": "rp4-v5-a3-report-receipt-v1",
        "update_id": update_id,
        "created_at_utc": snapshot["summary"]["created_at_utc"],
        "status": snapshot["summary"]["status"],
        "binding": snapshot["summary"]["binding"],
        "N_family_records": snapshot["summary"]["N_family_records"],
        "input_records_sha256": snapshot["summary"]["input_records_sha256"],
        "artifacts_sha256": {
            name: hashlib.sha256(value).hexdigest() for name, value in payloads.items()
        },
    }
    receipt_bytes = a2._json(receipt)
    if (destination / "receipt.json").exists() and (
        destination / "receipt.json"
    ).read_bytes() != receipt_bytes:
        raise ValueError("A3_REPORT_IMMUTABLE_RECEIPT_MISMATCH")
    for name, encoded in payloads.items():
        a2.write_bytes_once(destination / name, encoded)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=".rp4-a3-report-", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payloads["results_v5.md"])
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    a2.write_bytes_once(destination / "receipt.json", receipt_bytes)
    return receipt
