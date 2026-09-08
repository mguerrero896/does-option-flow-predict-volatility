"""Closed-record UTC, shared-mask, LightGBM-round and loss-tail diagnostics."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from artifacts.rp4_closeout_audit_code.audit_closed import (
    FAMILIES,
    OUTPUTS,
    PINS,
    ROOT,
    SETS,
    csv,
    load,
    new_file,
    sha,
    window_paths,
)


def run() -> dict[str, Any]:
    metadata, tails, masks = [], [], []
    first_binding: dict[tuple[int, str], dict[str, Any]] = {}
    reference = {}
    for horizon in [30, 15, 5]:
        for window in ["primary", "confirmation"]:
            public, private = window_paths(horizon, window)
            summary = load(public / "summary.json")
            for filename, digest in sorted(summary["completed_session_sha256"].items()):
                rec = load(private / "sessions" / filename, digest)
                binding = rec["binding"]
                known = first_binding.setdefault((horizon, window), binding)
                assert binding == known
                code = binding.get("code_sha256", binding.get("evaluation_code_sha256"))
                assert isinstance(code, dict)
                for path, expected in code.items():
                    full = ROOT / path
                    actual = PINS.setdefault(str(full), sha(full))
                    assert actual == expected
                session = rec["session"]
                keysha = hashlib.sha256(
                    json.dumps(rec["keys"], sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                end = dt.datetime.fromisoformat(rec["max_training_target_end_utc"])
                origin = dt.datetime.fromisoformat(rec["first_evaluation_origin_utc"])
                assert origin - end >= dt.timedelta(minutes=60)
                local_end = end.astimezone(ZoneInfo("America/New_York"))
                assert local_end.date().isoformat() == rec["train_last_session"]
                contract = (keysha, rec["train_sessions"], rec["train_last_session"], str(end))
                rkey = (window, session)
                if horizon == 30:
                    reference[rkey] = contract
                else:
                    assert reference[rkey] == contract
                masks.append(
                    {
                        "horizon_minutes": horizon,
                        "window": window,
                        "session": session,
                        "keys_sha256": keysha,
                        "same_keys_training_metadata_as_rv30": True,
                        **{f"mask_{k}": v for k, v in rec.get("mask_sha256", {}).items()},
                    }
                )
                metadata.append(
                    {
                        "horizon_minutes": horizon,
                        "window": window,
                        "session": session,
                        "max_training_target_end_utc": str(end),
                        "training_end_utc_clock": end.strftime("%H:%M"),
                        "training_end_ny_clock": local_end.strftime("%H:%M"),
                        "train_last_session": rec["train_last_session"],
                        "first_evaluation_origin_utc": str(origin),
                        "embargo_actual_minutes": (origin - end).total_seconds() / 60,
                        "binding_release_sha256": binding["release_sha256"],
                        "binding_constant_within_window": True,
                    }
                )
                target = np.asarray(rec["target"], dtype=float)
                for family in FAMILIES:
                    for info in SETS:
                        pred = np.asarray(rec["forecasts"][family][info], dtype=float)
                        ratio = target / np.maximum(pred, 1e-12)
                        loss = ratio - np.log(ratio) - 1
                        fit = rec["fits"][f"mean__{family}__{info}"]
                        tails.append(
                            {
                                "horizon_minutes": horizon,
                                "window": window,
                                "session": session,
                                "family": family,
                                "information_set": info,
                                "N_origins": len(loss),
                                "loss_above_5": int((loss > 5).sum()),
                                "max_qlike": float(loss.max()),
                                "selected_rounds": fit["selected"].get("rounds"),
                                "refit_rounds": fit.get("refit_rounds"),
                                "selected_leaves": fit["selected"].get("num_leaves"),
                            }
                        )
    maskframe = pd.DataFrame(masks)
    for window in ["primary", "confirmation"]:
        a = maskframe[(maskframe.window == window) & (maskframe.horizon_minutes == 15)]
        b = maskframe[(maskframe.window == window) & (maskframe.horizon_minutes == 5)]
        columns = [c for c in maskframe if c.startswith("mask_")]
        assert a.set_index("session")[columns].equals(b.set_index("session")[columns])
    csv("utc_purge_binding_by_session.csv", metadata)
    csv("cross_horizon_key_mask_parity.csv", masks)
    csv("loss_tails_and_rounds_by_session.csv", tails)
    t = pd.DataFrame(tails)
    totals = (
        t.groupby(["horizon_minutes", "window", "family", "information_set"])
        .agg(
            N_sessions=("session", "size"),
            N_origins=("N_origins", "sum"),
            loss_above_5=("loss_above_5", "sum"),
            max_qlike=("max_qlike", "max"),
            selected_rounds_min=("selected_rounds", "min"),
            selected_rounds_max=("selected_rounds", "max"),
        )
        .reset_index()
    )
    csv("loss_tails_and_rounds_summary.csv", totals)
    clocks = (
        pd.DataFrame(metadata)
        .groupby(["horizon_minutes", "window", "training_end_utc_clock", "training_end_ny_clock"])
        .size()
        .rename("N_sessions")
        .reset_index()
    )
    csv("training_end_clock_census.csv", clocks)
    result = {
        "status": "PASS_METADATA_ONLY",
        "sessions": len(metadata),
        "binding_constants": len(first_binding),
        "actual_embargo_min_minutes": min(row["embargo_actual_minutes"] for row in metadata),
        "cross_horizon_keys_training_metadata_exact": True,
        "rv15_rv5_bit_masks_exact": True,
        "rv30_bit_masks": (
            "Not persisted: keys, training-session count, last date and target-end "
            "metadata compared instead."
        ),
        "model_fits": 0,
        "new_p_values": 0,
        "bootstrap_runs": 0,
    }
    new_file("metadata_findings.json", (json.dumps(result, indent=2) + "\n").encode())
    new_file(
        "metadata_manifest.json",
        (
            json.dumps(
                {
                    "source_sha256": PINS,
                    "artifacts_sha256": OUTPUTS,
                    "producer_sha256": sha(Path(__file__)),
                    "model_fits": 0,
                    "new_p_values": 0,
                },
                indent=2,
            )
            + "\n"
        ).encode(),
    )
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
