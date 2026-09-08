"""Freeze the approved v4 horizon-only contract without reading new targets."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parent = root / "artifacts/rp4_v3_a1_empty_window/specification.json"
    prior = Path("artifacts/rp4_v4_prereg/protocol.md")
    panel = Path("private-input/1e60e265a1b78b1b0a71")
    pins = {
        parent: "930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5",
        prior: "6f8ad8d53a8f4336851415a99c25b316bf44db74165e29246110a3bb133eabee",
        panel: "a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637",
        root / "artifacts/rp4_v3_b2/summary.json": (
            "645d319f4b5b283a2b1bc6ecda1a185650b8436cdbf3b319e9debfc41210ef1d"
        ),
    }
    for path, expected in pins.items():
        if sha(path) != expected:
            raise ValueError(f"RP4_V4_FREEZE_PIN_MISMATCH:{path}")
    if prior.with_suffix(".sha256").read_text(encoding="utf-8").split()[0] != pins[prior]:
        raise ValueError("RP4_V4_PREREG_SIDECAR_MISMATCH")
    spec = json.loads(parent.read_text(encoding="utf-8"))
    if [len(spec["feature_sets"][name]) for name in ("B0", "B1", "B2")] != [29, 69, 138]:
        raise ValueError("RP4_V4_FEATURE_CONTRACT")
    spec.update(
        schema_version="rp4-walkforward-v4",
        parent_specification={"path": parent.as_posix(), "sha256": pins[parent]},
        parent_specification_sha256=pins[parent],
        base_panel={"path": panel.as_posix(), "sha256": pins[panel]},
        data_root="private-input/d983c44a81f6f3fe85fb",
        target_panel_relative_path="targets/panel.parquet",
        horizons={
            str(h): {"target_key": f"rv_{h}", "target_end_key": f"target_end_{h}_utc"}
            for h in (15, 5)
        },
        target_horizon_minutes=15,
        execution={
            "session_shards": 8,
            "threads_per_model": 4,
            "order": ["15/primary", "15/confirmation", "5/primary", "5/confirmation"],
        },
        endpoint_scope=["mean"],
        primary_horizon_minutes=15,
        secondary_horizon_minutes=5,
        mask_policy="exact_v3_eligibility_and_30min_causal_end_require_selected_target_finite_positive",
        target_reference={
            "path": (
                "private-input/47142047ee8ae2755cba"
                "rp2-v3-20260901-flow-session-loss-registration/"
                "rp2_block3_target/target_panel.parquet"
            ),
            "sha256": "fdab55c524a6ee2cd94bb3f1f544dec527e1c8813f9a03d6e17ed8029f842831",
            "bytes": 37068944,
        },
        bar_input_pins={
            "path": "private-input/31fd091340f440407b93",
            "sha256": "ca610184b4ccffe2d5792e86d8babefc12ebee52b38e5b1d16f8c2f7465606db",
        },
        target_validation={
            "strict_observed_closes": "h_plus_one",
            "comparison": "aligned_float64_bytes",
            "discrepancy": "investigate_before_evaluation",
            "reference_end": "2026-07-17",
            "confirmation_reference": "NONE",
        },
        preregistration={
            "path": prior.as_posix(),
            "sha256": pins[prior],
            "sidecar_sha256": sha(prior.with_suffix(".sha256")),
            "local_mtime_utc": datetime.fromtimestamp(prior.stat().st_mtime, UTC).isoformat(),
            "independent_timestamp_verified": False,
            "trigger_primary_v3_H2_p": {"log_ridge_harq": 0.0525, "lightgbm_qlike": 0.6631},
        },
        specification_md_path="docs/rp4/specification_v4.md",
        specification_md_sha256=sha(root / "docs/rp4/specification_v4.md"),
        decision_sha256=sha(root / "docs/rp4/decision_133_v4.md"),
        acquisition={"enabled": False},
    )
    spec["authority_decisions"].append(133)
    for key in ("jump_target", "tail_models", "candidate_gamma"):
        spec.pop(key, None)
    spec["model"].pop("mz_secondary")
    spec["model"]["lightgbm"]["initial_score"] = "log_training_mean_selected_target"
    spec["model"]["ridge"]["forecast_bounds_reference"] = (
        "positive_training_selected_target_linear_quantiles"
    )
    for key in ("auc", "mz"):
        spec["inference"].pop(key, None)
    spec["inference"]["fixed_sequence"]["joint_primary"] = (
        "both_contrasts_reject_in_at_least_one_family_at_15min_primary"
    )
    spec["inference"]["common_mask"] = spec["mask_policy"]
    out = root / "artifacts/rp4_v4_a1"
    if out.exists():
        raise FileExistsError("RP4_V4_A1_ALREADY_EXISTS")
    out.mkdir(parents=True)
    contract = out / "specification.json"
    contract.write_text(
        json.dumps(spec, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "stage": "A1",
        "status": "FROZEN_BEFORE_TARGET_MATERIALIZATION_AND_FITS",
        "frozen_at_utc": datetime.now(UTC).isoformat(),
        "input_sha256": {str(path): value for path, value in pins.items()},
        "specification_sha256": sha(contract),
        "specification_md_sha256": spec["specification_md_sha256"],
        "decision_sha256": spec["decision_sha256"],
        "freeze_code_sha256": sha(Path(__file__)),
        "new_targets_opened": 0,
        "model_fits": 0,
    }
    (out / "freeze_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
