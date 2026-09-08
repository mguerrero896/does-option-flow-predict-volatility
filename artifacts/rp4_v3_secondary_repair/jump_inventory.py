"""Verify closed v3 jump checkpoints and emit a target-value-free reuse inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from artifacts.rp4_code.evaluate import SETS, sha256, write_json_once
from artifacts.rp4_v3_code import evaluate_v3 as v3

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = Path("private-input/c43ac6756d25b8e9ea94")
NEW_ROOT = Path("private-input/e90b04c9636db3ce4b5d")
SPEC_PATH = ROOT / "artifacts/rp4_v3_a1_empty_window/specification.json"
SPEC_SHA = "930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5"
RELEASE_PATH = ROOT / "artifacts/rp4_v3_a2/evaluation_release.json"
RELEASE_SHA = "5e3046af023c9f41380307d62537aa4e8fc7514b23d51a95ea1f960ee23fe5bb"
ORIGINAL_RECEIPT_SHA = {
    "primary": "60c6f893a9f1b3f23b6737e6f022766e5a603b4225b4292359337356288178af",
    "confirmation": "698cd3067258f95c2ca3573618cda88f9fa1d3fda339def0f1455337767ac635",
}
MODELS = tuple(f"jump__{f}__{s}" for f in v3.FAMILIES for s in SETS)


def canonical_digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def read_verified(path: Path, expected: str) -> dict[str, Any]:
    encoded = path.read_bytes()
    if hashlib.sha256(encoded).hexdigest() != expected:
        raise ValueError("RP4_JUMP_INVENTORY_HASH_DRIFT:" + str(path))
    result: dict[str, Any] = json.loads(encoded)
    return result


def verify_component(
    path: Path,
    binding: dict[str, Any],
    session: str,
    keys: list[dict[str, Any]],
    labels: list[float],
) -> dict[str, Any]:
    """Never mistake a partial or nonconverged fit for a reusable component."""
    receipt_path = path.parent.parent / "session_receipts" / path.name
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("binding") != binding or receipt.get("session") != path.stem:
        raise ValueError("RP4_JUMP_INVENTORY_COMPONENT_RECEIPT_BINDING")
    component = read_verified(path, receipt["sha256"])
    if (
        path.stem not in MODELS
        or component.get("binding") != binding
        or component.get("session") != path.stem
        or component.get("evaluation_session") != session
        or component.get("forecast_scale") != "probability"
        or component.get("keys") != keys
        or component.get("target") != labels
        or len(component.get("forecast", [])) != len(keys)
        or any(not 0.0 < value < 1.0 for value in component["forecast"])
        or any(value not in (0.0, 1.0) for value in labels)
    ):
        raise ValueError("RP4_JUMP_INVENTORY_COMPONENT_CONTENT_DRIFT")
    fit = component["fit"]
    if "__log_ridge_harq__" in path.stem:
        if (
            fit["objective"] != "sum_binary_logloss_plus_lambda_l2_slopes"
            or fit["lambda_grid"] != [0.0001, 0.01, 1.0, 100.0, 10000.0]
            or len(fit["candidates"]) != 5
            or not fit["solver_refit"].get("converged", False)
            or any(not row["solver"].get("converged", False) for row in fit["candidates"])
        ):
            raise ValueError("RP4_JUMP_INVENTORY_UNCONVERGED_COMPONENT")
    elif fit["objective"] != "binary" or fit["method"] != "native_lightgbm_binary_jump":
        raise ValueError("RP4_JUMP_INVENTORY_WRONG_ENDPOINT_COMPONENT")
    return {
        "session": session,
        "model": path.stem,
        "N_origins": len(keys),
        "component_sha256": receipt["sha256"],
        "receipt_sha256": sha256(receipt_path),
        "keys_sha256": canonical_digest(keys),
        "labels_sha256": canonical_digest(labels),
    }


def audit_inventory() -> dict[str, Any]:
    spec = v3.load_spec(SPEC_PATH, SPEC_SHA)
    release = read_verified(RELEASE_PATH, RELEASE_SHA)
    if v3.evaluation_code_hashes() != release["evaluation_code_sha256"]:
        raise ValueError("RP4_JUMP_INVENTORY_FROZEN_CODE_DRIFT")
    windows = []
    input_pins = {str(SPEC_PATH): SPEC_SHA, str(RELEASE_PATH): RELEASE_SHA}
    for window, stage in (("primary", "b2"), ("confirmation", "b3")):
        folder = ROOT / f"artifacts/rp4_v3_{stage}"
        receipt_path = folder / "receipt.json"
        receipt = read_verified(receipt_path, ORIGINAL_RECEIPT_SHA[window])
        if (
            receipt.get("status") != "COMPLETE"
            or receipt.get("exit_code") != 0
            or receipt.get("window") != window
            or receipt.get("release_sha256") != RELEASE_SHA
        ):
            raise ValueError("RP4_JUMP_INVENTORY_UNCLOSED_OR_WRONG_WINDOW")
        expected_paths = {
            (folder / "summary.json").resolve(),
            (folder / "session_losses.csv").resolve(),
            (ORIGINAL / window / "fit_diagnostics.json").resolve(),
        }
        pins = {Path(k).resolve(): v for k, v in receipt["artifacts_sha256"].items()}
        if set(pins) != expected_paths or any(sha256(p) != digest for p, digest in pins.items()):
            raise ValueError("RP4_JUMP_INVENTORY_CLOSED_ARTIFACTS_DRIFT")
        input_pins[str(receipt_path)] = ORIGINAL_RECEIPT_SHA[window]
        input_pins.update({str(p): digest for p, digest in pins.items()})
        summary = read_verified(folder / "summary.json", pins[(folder / "summary.json").resolve()])
        binding = {
            "panel_sha256": release["panel_sha256"],
            "specification_sha256": SPEC_SHA,
            "release_sha256": RELEASE_SHA,
            "window": window,
            "code_sha256": release["evaluation_code_sha256"],
            "execution": release["execution"],
        }
        if summary["binding"] != binding:
            raise ValueError("RP4_JUMP_INVENTORY_SUMMARY_BINDING")
        session_pins = summary["completed_session_sha256"]
        if {p.name for p in (ORIGINAL / window / "sessions").glob("*.json")} != set(session_pins):
            raise ValueError("RP4_JUMP_INVENTORY_SESSION_FILE_SET")
        sessions = []
        components = []
        expected_components = set()
        for name, digest in sorted(session_pins.items()):
            session = Path(name).stem
            source = read_verified(ORIGINAL / window / "sessions" / name, digest)
            if source["session"] != session or source["binding"] != binding:
                raise ValueError("RP4_JUMP_INVENTORY_SESSION_BINDING")
            positions, labels = source["jump_positions"], source["jump_target"]
            if (
                positions != sorted(set(positions))
                or len(labels) != len(positions)
                or any(type(i) is not int or not 0 <= i < len(source["keys"]) for i in positions)
            ):
                raise ValueError("RP4_JUMP_INVENTORY_JUMP_POSITIONS")
            keys = [source["keys"][i] for i in positions]
            present = []
            for model in MODELS:
                path = ORIGINAL / window / "components" / session / "sessions" / f"{model}.json"
                if path.exists():
                    component = verify_component(path, binding, session, keys, labels)
                    component["relative_path"] = path.relative_to(ORIGINAL).as_posix()
                    components.append(component)
                    expected_components.add(path.resolve())
                    present.append(model)
            sessions.append(
                {
                    "session": session,
                    "source_session_sha256": digest,
                    "N_jump_origins": len(keys),
                    "keys_sha256": canonical_digest(keys),
                    "labels_sha256": canonical_digest(labels),
                    "reusable_models": present,
                    "missing_models": [model for model in MODELS if model not in present],
                    "original_endpoint_status": source["tail_status"]["jump"]["status"],
                }
            )
        observed_components = {
            p.resolve() for p in (ORIGINAL / window / "components").glob("*/sessions/jump__*.json")
        }
        if observed_components != expected_components or len(sessions) != summary["N_sessions"]:
            raise ValueError("RP4_JUMP_INVENTORY_COMPONENT_OR_SESSION_SET")
        counts = dict(sorted(Counter(c["model"] for c in components).items()))
        windows.append(
            {
                "window": window,
                "N_sessions": len(sessions),
                "component_counts": counts,
                "reusable_components": len(components),
                "missing_components": 6 * len(sessions) - len(components),
                "sessions": sessions,
                "components": components,
            }
        )
    return {
        "schema_version": "rp4-v3-jump-repair-original-inventory-v1",
        "status": "VERIFIED",
        "input_sha256": input_pins,
        "original_code_sha256": release["evaluation_code_sha256"],
        "original_panel_sha256": release["panel_sha256"],
        "specification_sha256": SPEC_SHA,
        "assets": spec["assets"],
        "windows": windows,
        "reusable_components": sum(w["reusable_components"] for w in windows),
        "missing_components": sum(w["missing_components"] for w in windows),
        "real_model_fits": 0,
        "raw_panel_reads": 0,
        "non_jump_estimates_computed": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = args.output.resolve()
    if not path.is_relative_to(NEW_ROOT) or path == NEW_ROOT:
        raise ValueError("RP4_JUMP_INVENTORY_OUTPUT_OUTSIDE_NEW_SCOPE")
    inventory = audit_inventory()
    write_json_once(path, inventory)
    print(
        json.dumps(
            {
                "status": inventory["status"],
                "path": str(path),
                "sha256": sha256(path),
                "reusable_components": inventory["reusable_components"],
                "missing_components": inventory["missing_components"],
                "real_model_fits": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
