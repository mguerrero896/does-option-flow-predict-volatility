"""Auditable A2 partial family reports; no readers, fitting, or implicit writes.

The runner supplies the exact A1 preflight calendar and verified worker records.
Probe records lack execution_sha256 and are deliberately inadmissible here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from artifacts.rp4_code.evaluate import write_bytes_once
from artifacts.rp4_v5_code import report as a1

from mds650.metrics import holm_adjust, qlike_losses

BASE_FAMILIES = a1.BASE_FAMILIES
SELECTORS = a1.SELECTORS
SETS = a1.SETS
HORIZONS = (15, 5, 30)
N_CALENDAR = 419
ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
EN_GRID = tuple((a, r) for a in (0.0001, 0.01, 1.0) for r in (0.1, 0.5, 0.9))
METRIC_COLUMNS = (
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
    "N_calendar",
    "status",
)
LOSS_COLUMNS = (
    "horizon_minutes",
    "session_date",
    "family",
    "information_set",
    "qlike",
    "mae",
    "mse",
    "N_origins",
    "N_asset_sessions",
)


def _json(value: Any) -> bytes:
    def convert(item: Any) -> Any:
        if isinstance(item, np.generic):
            return item.item()
        if isinstance(item, np.ndarray):
            return item.tolist()
        raise TypeError(f"A2_REPORT_NOT_JSON:{type(item).__name__}")

    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False, default=convert) + "\n"
    ).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value)).hexdigest()


def _session(value: Any) -> str:
    if (
        not isinstance(value, str)
        or date.fromisoformat(value).isoformat() != value
        or not "2024-10-28" <= value <= "2026-07-31"
    ):
        raise ValueError("A2_REPORT_SESSION_OUTSIDE_DEVELOPMENT")
    return value


def _calendar(expected_sessions: Sequence[str]) -> tuple[str, ...]:
    result = tuple(_session(value) for value in expected_sessions)
    if len(result) != N_CALENDAR or tuple(sorted(set(result))) != result:
        raise ValueError("A2_REPORT_EXACT_419_CALENDAR_REQUIRED")
    return result


def _number(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, (bool, str)) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"A2_REPORT_INVALID_{label}")
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0):
        raise ValueError(f"A2_REPORT_INVALID_{label}")
    return result


def _en_diagnostic(fit: Mapping[str, Any]) -> None:
    """Verify all nine inner candidates and the surviving refit ranking."""
    candidates = fit.get("candidates")
    exclusions = fit.get("candidate_exclusions")
    if not isinstance(candidates, list) or not isinstance(exclusions, list):
        raise ValueError("A2_REPORT_EN_CANDIDATE_DISCLOSURE_REQUIRED")
    indexed = {(row["alpha"], row["l1_ratio"]): row for row in candidates}
    if len(candidates) != len(EN_GRID) or set(indexed) != set(EN_GRID):
        raise ValueError("A2_REPORT_EN_INCOMPLETE_CANDIDATE_GRID")
    excluded: dict[str, set[tuple[float, float]]] = {"inner_fit": set(), "refit": set()}
    for row in exclusions:
        stage, key = row.get("stage"), (row.get("alpha"), row.get("l1_ratio"))
        if (
            stage not in excluded
            or key not in indexed
            or key[0] != 0.0001
            or key in excluded[stage]
            or not isinstance(row.get("reason"), str)
            or not row["reason"]
        ):
            raise ValueError("A2_REPORT_EN_UNREGISTERED_EXCLUSION")
        excluded[stage].add(key)
    for key, row in indexed.items():
        if row.get("status") == "excluded":
            if key not in excluded["inner_fit"] or row.get("validation_qlike") is not None:
                raise ValueError("A2_REPORT_EN_EXCLUSION_DISCLOSURE_MISMATCH")
        elif row.get("status") == "converged":
            _number(row.get("validation_qlike"), "EN_VALIDATION_SCORE")
            if key in excluded["inner_fit"]:
                raise ValueError("A2_REPORT_EN_EXCLUSION_DISCLOSURE_MISMATCH")
        else:
            raise ValueError("A2_REPORT_EN_CANDIDATE_STATUS")
    if any(indexed[key]["status"] != "converged" for key in excluded["refit"]):
        raise ValueError("A2_REPORT_EN_REFIT_BEFORE_VALIDATION")
    available = [
        key
        for key in EN_GRID
        if indexed[key]["status"] == "converged" and key not in excluded["refit"]
    ]
    if not available:
        raise ValueError("A2_REPORT_EN_NO_SURVIVING_CANDIDATE")
    expected = min(
        available, key=lambda key: (indexed[key]["validation_qlike"], EN_GRID.index(key))
    )
    selected = fit["selected"]
    if (selected.get("alpha"), selected.get("l1_ratio")) != expected or selected[
        "validation_qlike"
    ] != indexed[expected]["validation_qlike"]:
        raise ValueError("A2_REPORT_EN_VALIDATION_RANKING_MISMATCH")
    original_ranking = sorted(
        (key for key in EN_GRID if indexed[key]["status"] == "converged"),
        key=lambda key: (indexed[key]["validation_qlike"], EN_GRID.index(key)),
    )
    rank = original_ranking.index(expected)
    if (
        excluded["refit"] != set(original_ranking[:rank])
        or selected.get("selection_rank_after_refit_exclusions", rank + 1) != rank + 1
    ):
        raise ValueError("A2_REPORT_EN_REFIT_EXCLUSION_ORDER_MISMATCH")


def _flatten(records: Any) -> list[Mapping[str, Any]]:
    if isinstance(records, Mapping):
        if any(family not in BASE_FAMILIES for family in records):
            raise ValueError("A2_REPORT_UNKNOWN_FAMILY")
        result = [record for family in BASE_FAMILIES for record in records.get(family, [])]
        if any(record["family"] != family for family, rows in records.items() for record in rows):
            raise ValueError("A2_REPORT_FAMILY_CONTAINER_MISMATCH")
        return result
    return list(records)


def _validate(
    records: Any, expected_sessions: Sequence[str] | None = None
) -> list[Mapping[str, Any]]:
    rows = _flatten(records)
    calendar = set(_calendar(expected_sessions)) if expected_sessions is not None else None
    identities, key_by_session, target_by_session = set(), {}, {}
    common_binding = None
    for record in rows:
        family, horizon, session = (
            record["family"],
            record["horizon_minutes"],
            _session(record["session"]),
        )
        if family not in BASE_FAMILIES or isinstance(horizon, bool) or horizon not in HORIZONS:
            raise ValueError("A2_REPORT_UNKNOWN_FAMILY_OR_HORIZON")
        if calendar is not None and session not in calendar:
            raise ValueError("A2_REPORT_SESSION_NOT_IN_PREFLIGHT_CALENDAR")
        identity = (horizon, family, session)
        if identity in identities:
            raise ValueError("A2_REPORT_DUPLICATE_FAMILY_SESSION")
        identities.add(identity)
        binding = record["binding"]
        required = ("release_sha256", "specification_sha256", "execution_sha256")
        if not isinstance(binding, Mapping) or any(
            not isinstance(binding.get(key), str)
            or re.fullmatch("[0-9a-f]{64}", binding[key]) is None
            for key in required
        ):
            raise ValueError("A2_REPORT_WORKER_EXECUTION_BINDING_REQUIRED")
        encoded = _json(binding)
        if common_binding is not None and encoded != common_binding:
            raise ValueError("A2_REPORT_RELEASE_SPECIFICATION_EXECUTION_DRIFT")
        common_binding = encoded
        frame = pd.DataFrame(record["keys"])
        if (
            frame.empty
            or set(frame) != set(a1.KEYS)
            or frame[list(a1.KEYS)].isna().any().any()
            or frame.duplicated(list(a1.KEYS)).any()
            or not frame["session_date"].eq(session).all()
            or not frame["asset"].isin(ASSETS).all()
        ):
            raise ValueError("A2_REPORT_KEY_CONTRACT")
        minutes = frame["origin_minute"].to_numpy(dtype=float)
        if (
            not np.isfinite(minutes).all()
            or np.any(minutes != np.floor(minutes))
            or np.any(minutes < 0)
        ):
            raise ValueError("A2_REPORT_ORIGIN_MINUTE_INVALID")
        keys = tuple(frame[list(a1.KEYS)].itertuples(index=False, name=None))
        if session in key_by_session and keys != key_by_session[session]:
            raise ValueError("A2_REPORT_COMMON_KEYS_MISMATCH")
        key_by_session[session] = keys
        target = a1._positive(record["target"], len(frame))
        if (horizon, session) in target_by_session and not np.array_equal(
            target, target_by_session[horizon, session]
        ):
            raise ValueError("A2_REPORT_COMMON_TARGET_MISMATCH")
        target_by_session[horizon, session] = target
        if set(record["forecasts"]) != set(SETS) or set(record["fits"]) != set(SETS):
            raise ValueError("A2_REPORT_THREE_INFORMATION_SETS_REQUIRED")
        forecasts = {name: a1._positive(record["forecasts"][name], len(frame)) for name in SETS}
        if family == "seasonal_persistence" and any(
            not np.array_equal(forecasts["B0"], forecasts[name]) for name in SETS[1:]
        ):
            raise ValueError("A2_REPORT_SEASONAL_INFORMATION_SET_DRIFT")
        for name, fit in record["fits"].items():
            if fit.get("family", family) != family or fit.get("information_set", name) != name:
                raise ValueError("A2_REPORT_FIT_IDENTITY_MISMATCH")
            _number(fit.get("selected", {}).get("validation_qlike"), "VALIDATION_SCORE")
            if family == "log_elastic_net":
                _en_diagnostic(fit)
        _number(record["cpu_seconds"], "CPU_SECONDS", nonnegative=True)
        if (
            isinstance(record["shard"], bool)
            or not isinstance(record["shard"], int)
            or record["shard"] < 0
        ):
            raise ValueError("A2_REPORT_INVALID_SHARD")
    return sorted(
        rows,
        key=lambda row: (
            HORIZONS.index(row["horizon_minutes"]),
            BASE_FAMILIES.index(row["family"]),
            row["session"],
        ),
    )


def _session_losses(
    record: Mapping[str, Any], forecasts: Mapping[str, Any]
) -> list[dict[str, Any]]:
    actual = np.asarray(record["target"], dtype=float)
    asset = [key["asset"] for key in record["keys"]]
    result = []
    for family, sets in forecasts.items():
        for name in SETS:
            predicted = np.asarray(sets[name], dtype=float)
            with np.errstate(over="ignore", invalid="ignore"):
                errors = actual - predicted
                values = pd.DataFrame(
                    {
                        "asset": asset,
                        "qlike": qlike_losses(actual, predicted),
                        "mae": np.abs(errors),
                        "mse": np.square(errors),
                    }
                )
            if not np.isfinite(values[["qlike", "mae", "mse"]].to_numpy()).all():
                raise ValueError("A2_REPORT_NONFINITE_LOSS")
            means = values.groupby("asset")[["qlike", "mae", "mse"]].mean().mean()
            result.append(
                {
                    "horizon_minutes": record["horizon_minutes"],
                    "session_date": record["session"],
                    "family": family,
                    "information_set": name,
                    **means.to_dict(),
                    "N_origins": len(actual),
                    "N_asset_sessions": len(set(asset)),
                }
            )
    return result


def _table(losses: pd.DataFrame, *, calendar_verified: bool) -> pd.DataFrame:
    if losses.empty:
        return pd.DataFrame(columns=METRIC_COLUMNS)
    result = (
        losses.groupby(["horizon_minutes", "family", "information_set"], sort=False)
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
    result["rmse"] = np.sqrt(result.pop("mse"))
    result["version"], result["N_calendar"] = "v5", N_CALENDAR
    result["status"] = np.where(
        calendar_verified & result["N_sessions"].eq(N_CALENDAR), "COMPLETE", "PARTIAL"
    )
    return result[list(METRIC_COLUMNS)]


def summarize_family(
    records: Sequence[Mapping[str, Any]], *, expected_sessions: Sequence[str] | None = None
) -> pd.DataFrame:
    """Three accumulated metric rows; COMPLETE additionally requires the exact calendar."""
    rows = _validate(records, expected_sessions)
    if not rows or len({(row["family"], row["horizon_minutes"]) for row in rows}) != 1:
        raise ValueError("A2_REPORT_ONE_NONEMPTY_FAMILY_HORIZON_REQUIRED")
    if len(rows) > N_CALENDAR:
        raise ValueError("A2_REPORT_TOO_MANY_SESSIONS")
    losses = [
        loss for row in rows for loss in _session_losses(row, {row["family"]: row["forecasts"]})
    ]
    return _table(pd.DataFrame(losses), calendar_verified=expected_sessions is not None)


def assemble_sessions(per_family_records: Any) -> list[dict[str, Any]]:
    """Assemble complete six-family cells; validation scores alone determine selection."""
    grouped: dict[tuple[int, str], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for record in _validate(per_family_records):
        grouped[record["horizon_minutes"], record["session"]][record["family"]] = record
    assembled = []
    for (horizon, session), families in sorted(grouped.items()):
        if set(families) != set(BASE_FAMILIES):
            raise ValueError("A2_REPORT_SIX_FAMILY_CANDIDATES_REQUIRED")
        reference = families[BASE_FAMILIES[0]]
        forecasts = {family: dict(families[family]["forecasts"]) for family in BASE_FAMILIES}
        fits, selection = {}, {}
        for name in SETS:
            fits[name] = {family: families[family]["fits"][name] for family in BASE_FAMILIES}
            scores = {
                family: fits[name][family]["selected"]["validation_qlike"]
                for family in BASE_FAMILIES
            }
            order = sorted(
                BASE_FAMILIES, key=lambda family: (scores[family], BASE_FAMILIES.index(family))
            )
            selection[name] = {"primary": order[0], "top2": order[:2], "validation_qlike": scores}
            forecasts.setdefault(SELECTORS[0], {})[name] = list(forecasts[order[0]][name])
            forecasts.setdefault(SELECTORS[1], {})[name] = (
                (np.asarray(forecasts[order[0]][name]) + forecasts[order[1]][name]) / 2
            ).tolist()
        assembled.append(
            {
                "session": session,
                "horizon_minutes": horizon,
                "binding": {
                    **reference["binding"],
                    "window": "development",
                    "horizon_minutes": horizon,
                },
                "keys": reference["keys"],
                "target": reference["target"],
                "forecasts": forecasts,
                "selection": selection,
                "fits": fits,
            }
        )
    return assembled


def progress(records: Any, expected_sessions: Sequence[str]) -> pd.DataFrame:
    rows = _validate(records, expected_sessions)
    result = []
    for horizon in HORIZONS:
        for family in BASE_FAMILIES:
            subset = [
                row for row in rows if (row["horizon_minutes"], row["family"]) == (horizon, family)
            ]
            count = len(subset)
            result.append(
                {
                    "horizon_minutes": horizon,
                    "family": family,
                    "N_sessions": count,
                    "N_calendar": N_CALENDAR,
                    "N_remaining": N_CALENDAR - count,
                    "N_origins": sum(len(row["keys"]) for row in subset),
                    "cpu_seconds": sum(row["cpu_seconds"] for row in subset),
                    "status": "COMPLETE"
                    if count == N_CALENDAR
                    else "PARTIAL"
                    if count
                    else "PENDING",
                }
            )
    return pd.DataFrame(result)


def progress_line(frame: pd.DataFrame) -> str:
    return " | ".join(
        f"RV{horizon}: "
        + ", ".join(
            f"{row.family} {row.N_sessions}/{row.N_calendar}"
            for row in frame[frame["horizon_minutes"].eq(horizon)].itertuples()
        )
        for horizon in HORIZONS
    )


def _inference_spec(spec: Mapping[str, Any]) -> None:
    fixed = {**a1.INFERENCE, "alpha": 0.05, "version_bonferroni": 5}
    options = spec.get("inference", {})
    if any(key in options and options[key] != value for key, value in fixed.items()):
        raise ValueError("A2_REPORT_INFERENCE_SPECIFICATION_DRIFT")


def inference_horizon(
    losses: pd.DataFrame, expected_sessions: Sequence[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """A1 inference for one complete horizon; no placeholder horizons or interim tests."""
    calendar = _calendar(expected_sessions)
    if losses.empty or losses["horizon_minutes"].nunique() != 1:
        raise ValueError("A2_REPORT_ONE_COMPLETE_INFERENCE_HORIZON_REQUIRED")
    horizon = int(losses["horizon_minutes"].iloc[0])
    if horizon not in HORIZONS:
        raise ValueError("A2_REPORT_UNKNOWN_INFERENCE_HORIZON")
    if not set(LOSS_COLUMNS) <= set(losses) or set(losses["family"]) != set(a1.FAMILIES):
        raise ValueError("A2_REPORT_INFERENCE_REQUIRES_ALL_SIX_FAMILIES_AND_SELECTORS")
    for family in a1.FAMILIES:
        subset = losses[losses["family"].eq(family)]
        if subset.duplicated(["session_date", "information_set"]).any():
            raise ValueError("A2_REPORT_DUPLICATE_SELECTOR_LOSS")
        pivot = subset.pivot(
            index="session_date", columns="information_set", values="qlike"
        ).sort_index()
        if (
            tuple(pivot.index) != calendar
            or set(pivot.columns) != set(SETS)
            or not np.isfinite(pivot.to_numpy(dtype=float)).all()
        ):
            raise ValueError("A2_REPORT_INFERENCE_REQUIRES_EXACT_419_COMPLETE_SESSIONS")
    contrasts, chains = [], {}
    for selector in SELECTORS:
        subset = losses[losses["family"].eq(selector)]
        if subset.duplicated(["session_date", "information_set"]).any():
            raise ValueError("A2_REPORT_DUPLICATE_SELECTOR_LOSS")
        pivot = subset.pivot(
            index="session_date", columns="information_set", values="qlike"
        ).sort_index()
        if (
            tuple(pivot.index) != calendar
            or set(pivot.columns) != set(SETS)
            or not np.isfinite(pivot.to_numpy(dtype=float)).all()
        ):
            raise ValueError("A2_REPORT_INFERENCE_REQUIRES_EXACT_419_COMPLETE_SESSIONS")
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
                100 * result["estimate"] / denominator if available and denominator > 0 else None
            )
            contrasts.append(row)
            rows.append(row)
            opened = reject
        available = all(a1._available(row) for row in rows)
        chains[selector] = {
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


def _decision(contrasts: list[dict[str, Any]], chains: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        row for row in contrasts if row["horizon_minutes"] == 15 and row["family"] == SELECTORS[0]
    ]
    if not rows:
        return {
            "nominal_improves_v4": None,
            "nominal_status": "PENDING_RV15_COMPLETE",
            "v4_headline_replaced": False,
            "direct_v5_vs_v4_test": False,
        }
    h1, h2 = rows
    chain = next(
        row for row in chains if row["horizon_minutes"] == 15 and row["family"] == SELECTORS[0]
    )
    interval = h2.get("ci_low") is not None and h2.get("ci_high") is not None
    excludes = bool(interval and (h2["ci_low"] > 0 or h2["ci_high"] < 0))
    nominal = bool(a1._available(h2) and h2["estimate"] > 0 and h2["p_raw"] < 0.05 and excludes)
    return {
        "nominal_improves_v4": nominal,
        "nominal_status": "SATISFIED"
        if nominal
        else "NOT_SATISFIED"
        if a1._available(h2)
        else "NO_VERIFICABLE",
        "rule": (
            "RV15 selector_primary B2/B1: positive delta, one-sided p < 0.05, 95% CI excludes zero"
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
    }


def _frequencies(sessions: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    rows = []
    for horizon in HORIZONS:
        subset = [row for row in sessions if row["horizon_minutes"] == horizon]
        if not subset:
            continue
        for name in SETS:
            for family in BASE_FAMILIES:
                count = sum(row["selection"][name]["primary"] == family for row in subset)
                top2 = sum(family in row["selection"][name]["top2"] for row in subset)
                rows.append(
                    {
                        "horizon_minutes": horizon,
                        "information_set": name,
                        "family": family,
                        "selected_sessions": count,
                        "N_sessions": len(subset),
                        "selection_frequency": count / len(subset),
                        "top2_sessions": top2,
                        "mean_top2_weight": 0.5 * top2 / len(subset),
                    }
                )
    return pd.DataFrame(
        rows,
        columns=(
            "horizon_minutes",
            "information_set",
            "family",
            "selected_sessions",
            "N_sessions",
            "selection_frequency",
            "top2_sessions",
            "mean_top2_weight",
        ),
    )


def _candidate_tables(records: Sequence[Mapping[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frequencies, events = [], []
    for horizon in HORIZONS:
        subset = [
            row
            for row in records
            if row["family"] == "log_elastic_net" and row["horizon_minutes"] == horizon
        ]
        if not subset:
            continue
        for name in SETS:
            fits = [row["fits"][name] for row in subset]
            for row in subset:
                for exclusion in row["fits"][name]["candidate_exclusions"]:
                    events.append(
                        {
                            "horizon_minutes": horizon,
                            "session_date": row["session"],
                            "information_set": name,
                            "family": "log_elastic_net",
                            "stage": exclusion["stage"],
                            "alpha": exclusion["alpha"],
                            "l1_ratio": exclusion["l1_ratio"],
                            "reason": exclusion["reason"],
                            "diagnostics": _json(exclusion.get("diagnostics", {})).decode().strip(),
                        }
                    )
            for alpha, ratio in EN_GRID:
                key = (alpha, ratio)
                selected = sum(
                    (fit["selected"]["alpha"], fit["selected"]["l1_ratio"]) == key for fit in fits
                )
                active = sum(
                    any(
                        (candidate["alpha"], candidate["l1_ratio"]) == key
                        and candidate["status"] == "converged"
                        for candidate in fit["candidates"]
                    )
                    for fit in fits
                )
                for stage in ("inner_fit", "refit"):
                    excluded = sum(
                        any(
                            (item["alpha"], item["l1_ratio"]) == key and item["stage"] == stage
                            for item in fit["candidate_exclusions"]
                        )
                        for fit in fits
                    )
                    attempted = len(fits) if stage == "inner_fit" else selected + excluded
                    eligible = len(fits) if stage == "inner_fit" else active
                    frequencies.append(
                        {
                            "horizon_minutes": horizon,
                            "information_set": name,
                            "family": "log_elastic_net",
                            "stage": stage,
                            "alpha": alpha,
                            "l1_ratio": ratio,
                            "N_sessions": len(fits),
                            "N_calendar": N_CALENDAR,
                            "eligible_sessions": eligible,
                            "attempted_sessions": attempted,
                            "converged_sessions": attempted - excluded,
                            "excluded_sessions": excluded,
                            "active_after_stage_sessions": eligible - excluded,
                            "not_attempted_sessions": eligible - attempted,
                            "selected_sessions": selected,
                            "exclusion_frequency": excluded / len(fits),
                            "status": "COMPLETE" if len(fits) == N_CALENDAR else "PARTIAL",
                        }
                    )
    return pd.DataFrame(frequencies), pd.DataFrame(
        events,
        columns=(
            "horizon_minutes",
            "session_date",
            "information_set",
            "family",
            "stage",
            "alpha",
            "l1_ratio",
            "reason",
            "diagnostics",
        ),
    )


def _comparison(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    required = {
        "version",
        "horizon_minutes",
        "family",
        "information_set",
        "qlike",
        "mae",
        "rmse",
        "N_sessions",
        "N_origins",
    }
    identities = {
        ("v3" if h == 30 else "v4", h, family, name)
        for h in HORIZONS
        for family in ("log_ridge_harq", "lightgbm_qlike")
        for name in SETS
    }
    if (
        not required <= set(frame)
        or len(frame) != 18
        or set(
            frame[["version", "horizon_minutes", "family", "information_set"]].itertuples(
                index=False, name=None
            )
        )
        != identities
    ):
        raise ValueError("A2_REPORT_FROZEN_COMPARISON_IDENTITY_MISMATCH")
    numbers = frame[["qlike", "mae", "rmse", "N_sessions", "N_origins"]].to_numpy(dtype=float)
    if (
        not np.isfinite(numbers).all()
        or np.any(numbers < 0)
        or not frame["N_sessions"].eq(N_CALENDAR).all()
        or not frame["N_origins"].eq(160832).all()
    ):
        raise ValueError("A2_REPORT_FROZEN_COMPARISON_VALUES_INVALID")
    return frame.copy()


def build_snapshot(
    records: Any,
    spec: Mapping[str, Any],
    expected_sessions: Sequence[str],
    comparison: pd.DataFrame | None = None,
    gpu_control: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build only: partial family tables, completed-horizon selectors, and provenance."""
    calendar = _calendar(expected_sessions)
    _inference_spec(spec)
    rows = _validate(records, calendar)
    if any(key["asset"] not in spec["assets"] for row in rows for key in row["keys"]):
        raise ValueError("A2_REPORT_ASSET_SPECIFICATION_DRIFT")
    comparator = _comparison(comparison)
    counts = progress(rows, calendar)
    complete_horizons = [
        horizon
        for horizon in HORIZONS
        if counts[counts["horizon_minutes"].eq(horizon)]["N_sessions"].eq(N_CALENDAR).all()
    ]
    assembled = assemble_sessions(
        [row for row in rows if row["horizon_minutes"] in complete_horizons]
    )
    raw = [loss for row in rows for loss in _session_losses(row, {row["family"]: row["forecasts"]})]
    raw.extend(
        loss
        for row in assembled
        for loss in _session_losses(row, {family: row["forecasts"][family] for family in SELECTORS})
    )
    losses = pd.DataFrame(raw, columns=LOSS_COLUMNS)
    table = _table(losses, calendar_verified=True)
    frequencies = _frequencies(assembled)
    contrasts, chains = [], []
    if len(complete_horizons) == len(HORIZONS):
        inherited, losses, full_table, frequencies = a1.aggregate(assembled, spec)
        table = full_table.assign(N_calendar=N_CALENDAR, status="COMPLETE")[list(METRIC_COLUMNS)]
        contrasts, chains = inherited["contrasts"], inherited["selector_chains"]
    else:
        inherited = {}
        for horizon in complete_horizons:
            h_contrasts, h_chains = inference_horizon(
                losses[losses["horizon_minutes"].eq(horizon)], calendar
            )
            contrasts.extend(h_contrasts)
            chains.extend(h_chains)
    candidate_frequencies, exclusions = _candidate_tables(rows)
    summary = {
        **inherited,
        "schema_version": "rp4-v5-a2-snapshot-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "status": "COMPLETE" if len(complete_horizons) == 3 else "PARTIAL",
        "scope": "DEVELOPMENT_ONLY_FIFTH_HISTORICAL_READING",
        "N_calendar": N_CALENDAR,
        "expected_sessions": list(calendar),
        "calendar_sha256": _digest(list(calendar)),
        "N_family_records": len(rows),
        "input_records_sha256": _digest(rows),
        "binding": dict(rows[0]["binding"]) if rows else None,
        "completed_horizons": complete_horizons,
        "selector_inference_available_horizons": complete_horizons,
        "all_horizons_complete": len(complete_horizons) == 3,
        "inference_parameters": a1.INFERENCE.copy(),
        "contrasts": contrasts,
        "selector_chains": chains,
        "decision": inherited.get("decision", _decision(contrasts, chains)),
        "candidate_exclusion_events": len(exclusions),
        "comparison_sha256": hashlib.sha256(comparator.to_csv(index=False).encode()).hexdigest(),
        "amendment": spec.get("amendment", {}),
        "environment": spec.get("environment", {}),
        "gpu_control": dict(gpu_control)
        if gpu_control is not None
        else {
            "status": "PENDING",
            "reason": "device_and_shard_control.json not supplied",
        },
        "progress_line": progress_line(counts),
        "secondary_can_rescue_primary": False,
        "interval_scope": "pointwise two-sided percentile 95%; no simultaneous coverage claim",
        "multiplicity_scope": (
            "Holm of two chain maxima; times five is a declared version bound, "
            "not adaptive-search correction"
        ),
        "RESEARCH_ONLY": True,
        "capital_go": False,
        "disclaimer": "NOT INVESTMENT ADVICE",
    }
    snapshot = {
        "summary": summary,
        "table": table,
        "losses": losses,
        "frequencies": frequencies,
        "candidate_frequencies": candidate_frequencies,
        "exclusions": exclusions,
        "progress": counts,
        "comparison": comparator,
    }
    snapshot["markdown"] = _markdown(snapshot)
    return snapshot


def _markdown(snapshot: Mapping[str, Any]) -> str:
    summary = snapshot["summary"]
    complete = summary["completed_horizons"]
    decision = summary["decision"]
    environment_rows = [
        {"campo": key, "valor": json.dumps(value, sort_keys=True)}
        for key, value in summary["environment"].items()
    ]
    control_rows = [
        {"campo": key, "valor": json.dumps(value, sort_keys=True)}
        for key, value in summary["gpu_control"].items()
    ]
    contrast_columns = [
        "horizon_minutes",
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
    contrast_frame = pd.DataFrame(summary["contrasts"]).reindex(columns=contrast_columns)
    chain_frame = pd.DataFrame(summary["selector_chains"]).reindex(
        columns=[
            "horizon_minutes",
            "family",
            "q_chain",
            "p_holm_chain",
            "p_holm_chain_bonferroni5",
            "both_positive",
            "both_nominal_gates_rejected",
            "chain_holm_rejected",
        ]
    )
    parts = [
        "# RP4 v5 — intento A2, enmienda técnica 1",
        f"Estado global: **{summary['status']}**. Actualizado: {summary['created_at_utc']}.",
        "RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.",
        "## Progreso y cobertura",
        "El denominador es el calendario exacto de 419 sesiones del preflight A1. "
        "Las filas PARTIAL usan sólo las sesiones terminadas y pueden cubrir fechas distintas "
        "entre familias; no permiten declarar un ganador. Las métricas acumulan orígenes dentro "
        "de activo/sesión y después dan igual peso a activos y sesiones; "
        "RMSE toma la raíz al final.",
        a1._markdown(snapshot["progress"]),
        "## Métricas acumuladas por familia, conjunto y horizonte",
        a1._markdown(snapshot["table"]),
        "## Comparadores históricos conservados",
        "RV15/RV5 usan v4; RV30 usa v3. No existe aquí un comparador v4 de RV30. "
        "Las referencias completas no son una comparación pareada contra una tabla PARTIAL.",
        a1._markdown(snapshot["comparison"]),
        "## Selector e inferencia",
        f"Horizontes con las seis familias y las 419 sesiones completas: {complete or 'ninguno'}. "
        "El selector principal y el conjunto top2 sólo se muestran para esos horizontes. "
        "Ambos se fijan con QLIKE de validación temporal, "
        "antes de evaluar el objetivo de cada sesión.",
        a1._markdown(contrast_frame),
        a1._markdown(chain_frame),
        "H1 abre H2 sólo si se rechaza en dirección positiva al 5%. El p nominal H2 se conserva "
        "como diagnóstico aunque la puerta esté cerrada. Se usa max(pH1,pH2), Holm entre los dos "
        "selectores y Bonferroni ×5 como cota declarada entre versiones. Bootstrap de sesiones: "
        "bloque 5, 9.999 repeticiones, semilla 20260908; intervalos puntuales bilaterales del 95%.",
        f"Regla nominal RV15 B2/B1 del selector principal: {decision['nominal_status']}. "
        "Requiere delta positivo, p unilateral <0,05 e intervalo del 95% que excluya cero. "
        "Es distinta del resultado de la secuencia y Holm; no prueba una diferencia directa "
        "v5 frente a v4 ni reemplaza el titular v4.",
        "## Frecuencias de selección",
        a1._markdown(snapshot["frequencies"]),
        "## Elastic Net: candidatos activos y exclusiones",
        "Cada fila declara el denominador acumulado, la etapa inner_fit/refit, los candidatos "
        "intentados, convergentes, excluidos y todavía elegibles. Sólo se admite excluir la "
        "celda alpha=0,0001 por falta de convergencia registrada. El reajuste excluido obliga "
        "a usar el siguiente candidato según su QLIKE de validación; no se omite la familia.",
        a1._markdown(snapshot["candidate_frequencies"]),
        "### Exclusiones por sesión",
        a1._markdown(snapshot["exclusions"]),
        "## Alcance de la enmienda y custodia",
        "El intento A1 fallido y sus recibos se conservan por separado. Los ajustes de la sesión "
        "de calibración de memoria/GPU no se mezclan con los resultados de trabajadores. "
        "La rejilla MLP A2 contiene (64,32)/alpha=0,0001 y (32)/alpha=0,01; las otras dos "
        "configuraciones se retiraron de A2. A1 ya las ajustó en un componente: no se afirma "
        "que nunca se evaluaron. La enmienda mantiene estimandos, ventanas y regla de decisión.",
        "### Entorno y controles de dispositivo",
        "[Enmienda técnica 1](specification_v5_technical_amendment_1.md) · "
        "[recibo de control de dispositivo y fragmento]"
        "(../../artifacts/rp4_v5_a2/device_and_shard_control.json).",
        "Semilla registrada: 20260908. El backend, las versiones y la opción deterministic "
        "se divulgan según el entorno y los recibos siguientes; no se deduce determinismo "
        "GPU de una bandera CPU. Cuando falta el recibo de control, su estado es PENDING "
        "y no existe todavía una diferencia CPU/GPU medida para presentar.",
        a1._markdown(pd.DataFrame(environment_rows)),
        a1._markdown(pd.DataFrame(control_rows)),
        "El control repite la primera sesión RV15, 2024-10-28, con identidad de fragmento "
        "distinta. Para CPU se exige igualdad del hash; para GPU se divulgan las diferencias. "
        "LightGBM/MLP GPU se contrastan además con CPU usando el mismo backend, semilla y "
        "rejilla: diferencia absoluta y delta QLIKE, máxima diferencia de predicción y "
        "cualquier cambio de selección. Estos ajustes de control no cuentan como sesiones "
        "adicionales de evaluación.",
        "Binding: " + json.dumps(summary["binding"], sort_keys=True) + ".",
        "Calendario SHA256: " + summary["calendar_sha256"] + ". "
        "Registros SHA256: " + summary["input_records_sha256"] + ".",
    ]
    return "\n\n".join(parts) + "\n"


def write_snapshot(
    snapshot: Mapping[str, Any], snapshot_dir: Path, output: Path, *, update_id: str
) -> dict[str, Any]:
    """Publish immutable artifacts and an atomic current report; caller serializes updates."""
    if not isinstance(update_id, str) or not update_id:
        raise ValueError("A2_REPORT_UPDATE_ID_REQUIRED")
    destination, output = Path(snapshot_dir), Path(output)
    payloads = {
        "summary.json": _json(snapshot["summary"]),
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
        "schema_version": "rp4-v5-a2-report-receipt-v1",
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
    # Check the completed receipt before touching any current report on a retry.
    receipt_bytes = _json(receipt)
    if (destination / "receipt.json").exists() and (
        destination / "receipt.json"
    ).read_bytes() != receipt_bytes:
        raise ValueError("A2_REPORT_IMMUTABLE_RECEIPT_MISMATCH")
    for name, encoded in payloads.items():
        write_bytes_once(destination / name, encoded)
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=".rp4-a2-report-", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payloads["results_v5.md"])
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    write_bytes_once(destination / "receipt.json", receipt_bytes)
    return receipt
