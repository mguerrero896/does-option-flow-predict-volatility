"""Pure development-only tournament aggregation; report writing is explicit."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from artifacts.rp4_code.evaluate import write_bytes_once
from artifacts.rp4_v3_code import inference as inf

from mds650.metrics import holm_adjust, qlike_losses

BASE_FAMILIES = (
    "seasonal_persistence",
    "log_har",
    "log_ridge_harq",
    "log_elastic_net",
    "lightgbm_qlike",
    "mlp_log",
)
SELECTORS = ("selector_primary", "ensemble_top2")
FAMILIES = (*BASE_FAMILIES, *SELECTORS)
SETS = ("B0", "B1", "B2")
HORIZONS = (15, 5, 30)
KEYS = ("asset", "session_date", "origin_minute")
INFERENCE = {
    "statistic": "mean",
    "alternative": "greater",
    "repetitions": 9999,
    "block_length": 5,
    "seed": 20260908,
    "minimum_sessions": 10,
}


def _positive(value: Any, size: int) -> np.ndarray:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (size,) or not np.isfinite(vector).all() or (vector <= 0).any():
        raise ValueError("RP4_V5_REPORT_INVALID_POSITIVE_VECTOR")
    return vector


def _records(
    records: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, str]]:
    if not records:
        raise ValueError("RP4_V5_REPORT_NO_RECORDS")
    sessions: dict[int, dict[str, tuple[tuple[Any, ...], ...]]] = {h: {} for h in HORIZONS}
    bindings: dict[int, str] = {}
    common_binding = None
    losses, selections = [], []
    for record in records:
        horizon, session = record["horizon_minutes"], record["session"]
        if (
            isinstance(horizon, bool)
            or horizon not in HORIZONS
            or not isinstance(session, str)
            or date.fromisoformat(session).isoformat() != session
            or not "2024-10-28" <= session <= "2026-07-31"
        ):
            raise ValueError("RP4_V5_REPORT_UNREGISTERED_HORIZON_OR_SESSION")
        if session in sessions[horizon]:
            raise ValueError("RP4_V5_REPORT_DUPLICATE_HORIZON_SESSION")
        binding = record["binding"]
        if not isinstance(binding, Mapping) or not {
            "release_sha256",
            "specification_sha256",
            "horizon_minutes",
            "window",
        } <= set(binding):
            raise ValueError("RP4_V5_REPORT_BINDING_REQUIRED")
        if binding["horizon_minutes"] != horizon or binding["window"] != "development":
            raise ValueError("RP4_V5_REPORT_BINDING_SCOPE_DRIFT")
        inherited = json.dumps(
            {key: value for key, value in binding.items() if key != "horizon_minutes"},
            sort_keys=True,
            allow_nan=False,
        )
        if common_binding is not None and inherited != common_binding:
            raise ValueError("RP4_V5_REPORT_CROSS_HORIZON_BINDING_DRIFT")
        common_binding = inherited
        encoded = json.dumps(binding, sort_keys=True, allow_nan=False)
        if horizon in bindings and bindings[horizon] != encoded:
            raise ValueError("RP4_V5_REPORT_BINDING_DRIFT")
        bindings[horizon] = encoded
        frame = pd.DataFrame(record["keys"])
        if (
            frame.empty
            or set(frame) != set(KEYS)
            or frame[list(KEYS)].isna().any().any()
            or frame.duplicated(list(KEYS)).any()
            or not frame["session_date"].eq(session).all()
            or not frame["asset"].isin(spec["assets"]).all()
        ):
            raise ValueError("RP4_V5_REPORT_KEY_CONTRACT")
        minutes = frame["origin_minute"].to_numpy(dtype=float)
        if not np.isfinite(minutes).all() or np.any(minutes != np.floor(minutes)):
            raise ValueError("RP4_V5_REPORT_ORIGIN_MINUTE_INVALID")
        sessions[horizon][session] = tuple(frame[list(KEYS)].itertuples(index=False, name=None))
        actual = _positive(record["target"], len(frame))
        supplied = record["forecasts"]
        if set(supplied) != set(FAMILIES):
            raise ValueError("RP4_V5_REPORT_COMMON_FAMILIES_REQUIRED")
        forecasts = {}
        for family in FAMILIES:
            if set(supplied[family]) != set(SETS):
                raise ValueError("RP4_V5_REPORT_COMMON_INFORMATION_SETS_REQUIRED")
            forecasts[family] = {
                name: _positive(supplied[family][name], len(frame)) for name in SETS
            }
        if any(
            not np.array_equal(
                forecasts["seasonal_persistence"]["B0"], forecasts["seasonal_persistence"][name]
            )
            for name in SETS[1:]
        ):
            raise ValueError("RP4_V5_REPORT_SEASONAL_INFORMATION_SET_DRIFT")
        if set(record["selection"]) != set(SETS):
            raise ValueError("RP4_V5_REPORT_SELECTION_SETS_REQUIRED")
        for name in SETS:
            chosen = record["selection"][name]
            primary, top2 = chosen["primary"], chosen["top2"]
            if (
                primary not in BASE_FAMILIES
                or not isinstance(top2, (list, tuple))
                or len(top2) != 2
                or len(set(top2)) != 2
                or any(family not in BASE_FAMILIES for family in top2)
                or top2[0] != primary
            ):
                raise ValueError("RP4_V5_REPORT_SELECTION_CONTRACT")
            scores = chosen.get("validation_qlike")
            if not isinstance(scores, Mapping) or set(scores) != set(BASE_FAMILIES):
                raise ValueError("RP4_V5_REPORT_SIX_VALIDATION_SCORES_REQUIRED")
            if any(
                isinstance(value, bool) or not math.isfinite(value) for value in scores.values()
            ):
                raise ValueError("RP4_V5_REPORT_VALIDATION_SCORE_NONFINITE")
            ranking = sorted(
                BASE_FAMILIES, key=lambda family: (scores[family], BASE_FAMILIES.index(family))
            )
            if primary != ranking[0] or list(top2) != ranking[:2]:
                raise ValueError("RP4_V5_REPORT_VALIDATION_RANKING_MISMATCH")
            if "fits" in record:
                fitted = record["fits"].get(name, {})
                if set(fitted) != set(BASE_FAMILIES) or any(
                    fitted[family].get("selected", {}).get("validation_qlike") != scores[family]
                    for family in BASE_FAMILIES
                ):
                    raise ValueError("RP4_V5_REPORT_VALIDATION_FIT_RECEIPT_MISMATCH")
            if not np.array_equal(forecasts["selector_primary"][name], forecasts[primary][name]):
                raise ValueError("RP4_V5_REPORT_PRIMARY_FORECAST_SELECTION_MISMATCH")
            expected = (forecasts[top2[0]][name] + forecasts[top2[1]][name]) / 2.0
            if not np.array_equal(forecasts["ensemble_top2"][name], expected):
                raise ValueError("RP4_V5_REPORT_ENSEMBLE_FORECAST_SELECTION_MISMATCH")
            selections.append(
                {
                    "horizon_minutes": horizon,
                    "session_date": session,
                    "information_set": name,
                    "primary": primary,
                    "top2": list(top2),
                }
            )
        for family in FAMILIES:
            for name in SETS:
                predicted = forecasts[family][name]
                errors = actual - predicted
                with np.errstate(over="ignore", invalid="ignore"):
                    values = pd.DataFrame(
                        {
                            "asset": frame["asset"],
                            "qlike": qlike_losses(actual, predicted),
                            "mae": np.abs(errors),
                            "mse": np.square(errors),
                        }
                    )
                if not np.isfinite(values[["qlike", "mae", "mse"]].to_numpy()).all():
                    raise ValueError("RP4_V5_REPORT_NONFINITE_LOSS")
                means = values.groupby("asset")[["qlike", "mae", "mse"]].mean().mean()
                losses.append(
                    {
                        "horizon_minutes": horizon,
                        "session_date": session,
                        "family": family,
                        "information_set": name,
                        **means.to_dict(),
                        "N_origins": len(frame),
                        "N_asset_sessions": int(frame["asset"].nunique()),
                    }
                )
    reference = sessions[15]
    if not reference or len(reference) > 419 or any(sessions[h] != reference for h in (5, 30)):
        raise ValueError("RP4_V5_REPORT_HORIZON_MASK_OR_SESSION_DRIFT")
    return losses, selections, bindings


def _available(result: Mapping[str, Any]) -> bool:
    return bool(
        result.get("status") == "COMPUTED"
        and result.get("p_raw") is not None
        and result.get("estimate") is not None
        and math.isfinite(result["p_raw"])
        and 0 <= result["p_raw"] <= 1
        and math.isfinite(result["estimate"])
    )


def _inference(losses: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contrasts, chains = [], []
    for horizon in HORIZONS:
        horizon_chains = {}
        for selector in SELECTORS:
            subset = losses[(losses["horizon_minutes"] == horizon) & (losses["family"] == selector)]
            pivot = subset.pivot(
                index="session_date", columns="information_set", values="qlike"
            ).sort_index()
            opened, rows = True, []
            for contrast, base, expanded in inf.CONTRASTS:
                result = inf.session_contrast(
                    (pivot[base] - pivot[expanded]).to_numpy(), **INFERENCE
                )
                available = _available(result)
                reject = bool(
                    opened and available and result["estimate"] > 0 and result["p_raw"] <= 0.05
                )
                row = {
                    **result,
                    "horizon_minutes": horizon,
                    "family": selector,
                    "contrast": contrast,
                    "inference_role": "PRIMARY" if horizon == 15 else "SECONDARY",
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
                    100 * result["estimate"] / denominator
                    if available and denominator > 0
                    else None
                )
                contrasts.append(row)
                rows.append(row)
                opened = reject
            available = all(_available(row) for row in rows)
            horizon_chains[selector] = {
                "horizon_minutes": horizon,
                "family": selector,
                "inference_role": "PRIMARY" if horizon == 15 else "SECONDARY",
                "q_chain": max(row["p_raw"] for row in rows) if available else None,
                "both_positive": available and all(row["estimate"] > 0 for row in rows),
                "both_nominal_gates_rejected": opened,
                "holm_unavailable_treated_as_one": not available,
            }
        adjusted = holm_adjust(
            {
                selector: chain["q_chain"] if chain["q_chain"] is not None else 1.0
                for selector, chain in horizon_chains.items()
            }
        )
        for selector, chain in horizon_chains.items():
            value = adjusted[selector] if chain["q_chain"] is not None else None
            chain.update(
                p_holm_chain=value,
                p_holm_chain_bonferroni5=min(1.0, 5.0 * value) if value is not None else None,
                chain_holm_rejected=bool(
                    chain["both_positive"] and value is not None and value <= 0.05
                ),
                holm_family_size=2,
            )
            chains.append(chain)
    return contrasts, chains


def aggregate(
    records: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Aggregate all three complete development horizons; never fit or read files.

    The runner owns the exact 419-session schedule and skipped-session census.
    Here records must have identical evaluated sessions and origin keys at every
    horizon. Losses are long-form, one row per session/family/information set.
    """
    options = spec.get("inference", {})
    fixed = {**INFERENCE, "alpha": 0.05, "version_bonferroni": 5}
    if any(key in options and options[key] != value for key, value in fixed.items()):
        raise ValueError("RP4_V5_REPORT_INFERENCE_SPECIFICATION_DRIFT")
    raw_losses, selections, bindings = _records(records, spec)
    losses = pd.DataFrame(raw_losses).sort_values(
        ["horizon_minutes", "session_date", "family", "information_set"], ignore_index=True
    )
    table = (
        losses.groupby(["horizon_minutes", "family", "information_set"], sort=True)
        .agg(
            qlike=("qlike", "mean"),
            mae=("mae", "mean"),
            mse=("mse", "mean"),
            N_sessions=("session_date", "size"),
            N_origins=("N_origins", "sum"),
            N_asset_sessions=("N_asset_sessions", "sum"),
        )
        .reset_index()
    )
    table["rmse"] = np.sqrt(table.pop("mse"))
    table.insert(0, "version", "v5")
    table = table[
        [
            "version",
            "horizon_minutes",
            "family",
            "information_set",
            "qlike",
            "mae",
            "rmse",
            "N_sessions",
            "N_origins",
            "N_asset_sessions",
        ]
    ]
    frequency_rows = []
    for horizon in HORIZONS:
        for name in SETS:
            chosen = [
                r
                for r in selections
                if r["horizon_minutes"] == horizon and r["information_set"] == name
            ]
            for family in BASE_FAMILIES:
                count = sum(r["primary"] == family for r in chosen)
                top2_count = sum(family in r["top2"] for r in chosen)
                frequency_rows.append(
                    {
                        "horizon_minutes": horizon,
                        "information_set": name,
                        "family": family,
                        "selected_sessions": count,
                        "N_sessions": len(chosen),
                        "selection_frequency": count / len(chosen),
                        "top2_sessions": top2_count,
                        "mean_top2_weight": 0.5 * top2_count / len(chosen),
                    }
                )
    frequencies = pd.DataFrame(frequency_rows)
    contrasts, chains = _inference(losses)
    h1, h2 = [
        row for row in contrasts if row["horizon_minutes"] == 15 and row["family"] == SELECTORS[0]
    ]
    chain = next(
        row for row in chains if row["horizon_minutes"] == 15 and row["family"] == SELECTORS[0]
    )
    interval_available = h2.get("ci_low") is not None and h2.get("ci_high") is not None
    interval_excludes_zero = bool(interval_available and (h2["ci_low"] > 0 or h2["ci_high"] < 0))
    nominal = bool(
        _available(h2) and h2["estimate"] > 0 and h2["p_raw"] < 0.05 and interval_excludes_zero
    )
    evaluated = losses[losses["horizon_minutes"] == 15]["session_date"].nunique()
    summary = {
        "schema_version": "rp4-v5-aggregate-v1",
        "status": "COMPUTED",
        "scope": "DEVELOPMENT_ONLY_FIFTH_HISTORICAL_READING",
        "scheduled_sessions": 419,
        "evaluated_sessions_per_horizon": int(evaluated),
        "scheduled_minus_evaluated_sessions": 419 - int(evaluated),
        "schedule_census_owner": "runner; aggregation verifies common evaluated sessions and keys",
        "first_evaluated_session": str(losses["session_date"].min()),
        "last_evaluated_session": str(losses["session_date"].max()),
        "horizons": list(HORIZONS),
        "primary_horizon_minutes": 15,
        "N_table_rows": len(table),
        "N_frequency_rows": len(frequencies),
        "binding_by_horizon": {str(h): json.loads(value) for h, value in bindings.items()},
        "inference_parameters": INFERENCE.copy(),
        "contrasts": contrasts,
        "selector_chains": chains,
        "decision": {
            "nominal_improves_v4": nominal,
            "nominal_status": "SATISFIED"
            if nominal
            else "NOT_SATISFIED"
            if _available(h2)
            else "NO_VERIFICABLE",
            "rule": (
                "RV15 selector_primary B2/B1: positive delta, "
                "one-sided p < 0.05, 95% CI excludes zero"
            ),
            "estimate": h2["estimate"],
            "p_raw": h2["p_raw"],
            "ci_low": h2["ci_low"],
            "ci_high": h2["ci_high"],
            "h1_gate_rejected": h1["rejected"],
            "chain_holm_rejected": chain["chain_holm_rejected"],
            "nominal_and_h1_and_chain_holm": nominal
            and h1["rejected"]
            and chain["chain_holm_rejected"],
            "v4_headline_replaced": False,
            "direct_v5_vs_v4_test": False,
        },
        "interval_scope": "pointwise two-sided percentile 95%; no simultaneous coverage claim",
        "multiplicity_scope": (
            "Holm of two chain maxima; times five is a declared version bound, "
            "not adaptive-search correction"
        ),
        "secondary_can_rescue_primary": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
        "disclaimer": "NOT INVESTMENT ADVICE",
    }
    return summary, losses, table, frequencies


def _markdown(frame: pd.DataFrame) -> str:
    """Render a small Markdown table without optional tabulate dependencies."""
    if frame.empty:
        return "NO DISPONIBLE."

    def cell(value: Any) -> str:
        if value is None or (isinstance(value, (float, np.floating)) and not math.isfinite(value)):
            return "NO DISPONIBLE"
        if isinstance(value, (bool, np.bool_)):
            return "sí" if value else "no"
        text = f"{value:.8g}" if isinstance(value, (float, np.floating)) else str(value)
        return text.replace("|", "\\|").replace("\r\n", "<br>").replace("\n", "<br>")

    lines = [
        "| " + " | ".join(map(str, frame.columns)) + " |",
        "| " + " | ".join("---" for _ in frame.columns) + " |",
    ]
    lines.extend(
        "| " + " | ".join(cell(v) for v in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    )
    return "\n".join(lines)


def write_report(
    summary: Mapping[str, Any],
    table: pd.DataFrame,
    frequencies: pd.DataFrame,
    output: Path,
    comparison: pd.DataFrame | None = None,
    chronology: list[Any] | None = None,
) -> Path:
    """Write the explicit Markdown output once; caller supplies frozen comparators.

    Comparison columns are the table schema; ``version`` must be ``v4`` for
    RV5/RV15 and ``v3`` for RV30. Unavailable comparator metrics remain missing.
    """
    combined = table.copy()
    if comparison is not None and not comparison.empty:
        required = {"version", "horizon_minutes", "family", "information_set"}
        if not required <= set(comparison):
            raise ValueError("RP4_V5_REPORT_COMPARISON_SCHEMA")
        expected = comparison["horizon_minutes"].map({5: "v4", 15: "v4", 30: "v3"})
        if (
            expected.isna().any()
            or not comparison["version"].eq(expected).all()
            or not comparison["information_set"].isin(SETS).all()
            or comparison.duplicated(sorted(required)).any()
        ):
            raise ValueError("RP4_V5_REPORT_COMPARISON_VERSION_OR_KEYS")
        combined = pd.concat(
            [combined, comparison.reindex(columns=table.columns)], ignore_index=True
        )
    decision = summary["decision"]
    contrasts = pd.DataFrame(summary["contrasts"])
    chains = pd.DataFrame(summary["selector_chains"])
    chronology_text = "No se adjuntó cronología del ejecutor."
    if chronology:
        chronology_text = "\n".join(
            "- "
            + (
                json.dumps(item, ensure_ascii=False, sort_keys=True)
                if isinstance(item, dict)
                else str(item)
            )
            for item in chronology
        )
    result = "cumple" if decision["nominal_improves_v4"] else "no cumple"
    text = (
        "# RP4 v5 — resultados del torneo de familias\n\n"
        "RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false.\n\n"
        f"El selector primario RV15 **{result}** la regla nominal del propietario "
        f"(estado: {decision['nominal_status']}). "
        "v4 conserva el titular hasta respaldo prospectivo. "
        "La regla evalúa el incremento B2/B1 dentro de v5; "
        "no prueba una diferencia directa entre versiones.\n\n"
        f"Calendario: {summary['scheduled_sessions']} sesiones programadas; "
        f"{summary['evaluated_sessions_per_horizon']} evaluadas por horizonte, "
        f"{summary['first_evaluated_session']}–{summary['last_evaluated_session']}. "
        "La diferencia debe quedar explicada por el censo del ejecutor, nunca como pérdidas cero. "
        "Sólo desarrollo; sin lectura prospectiva.\n\n"
        "## Familia × conjunto × horizonte\n\n"
        "QLIKE/MAE: media por activo/sesión, luego igual por sesión. RMSE: raíz al final "
        "de la misma media de errores cuadrados. RV30 usa v3 como referencia; v4 no ejecutó RV30. "
        "NO DISPONIBLE identifica métricas no aportadas, no ceros.\n\n"
        + _markdown(
            combined.sort_values(["horizon_minutes", "information_set", "version", "family"])
        )
        + "\n\n## Frecuencias de selección\n\n"
        "El denominador son sesiones evaluadas por conjunto/horizonte. "
        "Incluye familias nunca elegidas; "
        "los pesos medios top2 suman uno.\n\n"
        + _markdown(frequencies)
        + "\n\n## Deltas pareados y puertas nominales\n\n"
        "Delta = pérdida base − ampliada: positivo favorece el conjunto ampliado. "
        "Bootstrap circular: bloques de cinco sesiones, 9999 réplicas, semilla 20260908. "
        "IC95% puntuales bilaterales percentiles; "
        "p unilaterales con nula centrada y corrección +1. "
        "H2 cerrada conserva p nominal diagnóstico.\n\n"
        + _markdown(
            contrasts[
                [
                    "horizon_minutes",
                    "family",
                    "contrast",
                    "estimate",
                    "ci_low",
                    "ci_high",
                    "p_nominal",
                    "p_bonferroni5",
                    "hypothesis_status",
                    "p_for_decision",
                ]
            ]
        )
        + "\n\n## Holm entre las dos cadenas de selectores\n\n"
        "q=max(p_H1,p_H2); Holm entre los dos q, con ambos efectos positivos. "
        "La cota Bonferroni ×5 no elimina la adaptación histórica ni ajusta los IC. "
        "RV5/RV30 son secundarios y no rescatan RV15.\n\n"
        + _markdown(chains)
        + "\n\n## Regla nominal y alcance\n\n"
        + _markdown(pd.DataFrame([decision]))
        + "\n\nQuinta lectura retrospectiva del desarrollo. La selección interna evita que "
        "el objetivo de la sesión decida el ganador, pero no convierte estas ventanas reutilizadas "
        "en una confirmación independiente. La validez del ajuste y la selección se acredita "
        "mediante sus recibos; la agregación verifica sus pronósticos, claves y muestra común.\n\n"
        "## Cronología\n\n" + chronology_text + "\n"
    )
    write_bytes_once(output, text.encode("utf-8"))
    return output
