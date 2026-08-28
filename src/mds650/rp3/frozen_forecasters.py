"""The frozen forecasters of the RP3 program: trained once, serialized, never adapted.

`docs/rp3/PREREGISTRATION.md` (committed-blob SHA-256
`66906a88b0d8ff76d9bbc6556e0aa64e32de494254d2ebdccc49140fce7f77e7`) commits the program to
a frozen design: the B1 model and the B1-plus-index model are trained on data through
2026-07-17 only, serialized with recorded hashes, and every session after that date is
evaluation — scored by these exact bytes, never trained on, never recalibrated toward.

Three decisions here are load-bearing and are recorded in the freeze manifest rather than
left to be rediscovered:

- **The index keeps its own preprocessor.** The frozen theta of
  `artifacts/rp3/b2_index_theta.json` was fitted on the B2 design of the development
  role's 60 % training fold, and a linear index is only the frozen index when its inputs
  are standardised with the statistics theta was fitted against. The theta artifact
  records the coefficients but not those fold statistics, so the freeze recomputes them —
  deterministically, from the same content-hashed parquets the theta names — verifies the
  reproduced index matches theta's recorded train mean and standard deviation, and
  persists the statistics in the manifest. The models' own preprocessor is a different
  object, fitted on every pre-window row, and the two must never be conflated.
- **Training is every pre-window row.** The 60/40 chronological split existed to score
  development contrasts; the program's read scores virgin sessions instead, so holding
  back 40 % of history would spend data on a purpose the design no longer has. Early
  stopping still needs held-out rows, and takes them the way the ladder always has:
  the last fifth of the *training* sessions, inside `_fit_boosted`.
- **Serialization is verified at freeze time.** The freeze reloads its own output from
  disk and re-predicts the training rows; a byte that does not survive the round trip
  fails the freeze rather than surfacing in 2029 at the single read.

The window boundary is enforced here, not promised: training refuses any input row after
2026-07-17, and prediction refuses evaluation rows on or before it unless the caller
explicitly says it is re-scoring the training window (which the freeze's own round-trip
verification is, and the read never is).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import lightgbm
import numpy as np
import numpy.typing as npt
import polars as pl

from mds650.rp2.ladder import VARIANCE_FLOOR, _fit_boosted
from mds650.rp2.panel import (
    B0_FEATURES,
    B1_FEATURES,
    B2_FEATURES,
    chronological_split,
    common_evaluation_mask,
    load_merged_panel,
    session_rank,
)
from mds650.rp2.preprocessing import (
    FittedPreprocessor,
    fit_preprocessor,
    transform_features,
)
from mds650.rp2.qlike_objective import EXPONENT_CLIP, lightgbm_metric, lightgbm_objective

type FloatArray = npt.NDArray[np.float64]
type BoolArray = npt.NDArray[np.bool_]

#: Last session the program may train on; first evaluation session is the next business
#: day. The same constant the preregistration states in prose, and the guards assert.
TRAINING_WINDOW_END: Final = "2026-07-17"
#: LightGBM seed, identical to the ladder's, so the frozen fit is the family the
#: development cell was measured in and not a sibling.
SEED: Final = 20260818
#: The two model names the manifest records; every consumer addresses them by these keys.
BASE_MODEL: Final = "b1"
EXPANDED_MODEL: Final = "b1_plus_index"

MANIFEST_NAME: Final = "freeze_manifest.json"
_MODEL_FILES: Final = {BASE_MODEL: "b1_model.txt", EXPANDED_MODEL: "b1_plus_index_model.txt"}

#: Tolerance for the freeze-time round trip and for the index-reproduction check. The
#: booster string format prints doubles at full precision, so the round trip should be
#: exact; the tolerance exists to name the failure, not to absorb drift.
ROUND_TRIP_TOLERANCE: Final = 1e-9


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: dict[str, object]) -> str:
    body = {key: value for key, value in payload.items() if key != "self_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _preprocessor_payload(fitted: FittedPreprocessor) -> dict[str, object]:
    return {
        "medians": dict(fitted.medians),
        "means": dict(fitted.means),
        "scales": dict(fitted.scales),
        "missing_indicator_features": list(fitted.missing_indicator_features),
        "features": list(fitted.features),
    }


def _preprocessor_from_payload(payload: dict[str, object]) -> FittedPreprocessor:
    medians = payload["medians"]
    means = payload["means"]
    scales = payload["scales"]
    indicators = payload["missing_indicator_features"]
    features = payload["features"]
    assert isinstance(medians, dict)
    assert isinstance(means, dict)
    assert isinstance(scales, dict)
    assert isinstance(indicators, list)
    assert isinstance(features, list)
    return FittedPreprocessor(
        medians={str(k): float(v) for k, v in medians.items()},
        means={str(k): float(v) for k, v in means.items()},
        scales={str(k): float(v) for k, v in scales.items()},
        missing_indicator_features=tuple(str(name) for name in indicators),
        features=tuple(str(name) for name in features),
    )


def _assert_training_window(frame: pl.DataFrame) -> str:
    """Refuse to train past the window end; return the latest session actually present."""

    latest = str(frame["session_date"].max())
    if latest > TRAINING_WINDOW_END:
        raise ValueError(f"RP3_FREEZE_WINDOW_VIOLATION:{latest}")
    return latest


@dataclass(frozen=True)
class FrozenForecasters:
    """The deserialized program: two boosters, two preprocessors, one frozen index."""

    manifest: dict[str, object]
    boosters: dict[str, lightgbm.Booster]
    init_scores: dict[str, float]
    model_preprocessor: FittedPreprocessor
    index_preprocessor: FittedPreprocessor
    theta: FloatArray
    index_mean: float
    index_std: float
    index_epsilon: float

    def index_values(self, frame: pl.DataFrame) -> FloatArray:
        """The frozen linear index for every row of ``frame``."""

        design = transform_features(
            frame,
            list(self.index_preprocessor.features),
            self.index_preprocessor,
            intercept=False,
        )
        columns = self.index_preprocessor.column_names(intercept=False)
        expected = self.manifest["index"]
        assert isinstance(expected, dict)
        if list(columns) != expected["design_columns"]:
            raise ValueError("RP3_FROZEN_INDEX_COLUMNS_MISMATCH")
        return np.asarray(
            (design @ self.theta - self.index_mean) / (self.index_std + self.index_epsilon),
            dtype=np.float64,
        )

    def predict(
        self, frame: pl.DataFrame, *, allow_training_window: bool = False
    ) -> dict[str, FloatArray]:
        """Score rows with the frozen models; refuses pre-window rows unless told.

        The refusal direction is deliberate: at read time every scored session must be
        virgin, and a silent re-score of history would let training rows into the
        evaluation bank. The freeze's own round-trip verification is the one caller that
        legitimately re-scores history, and it says so.
        """

        if not allow_training_window:
            earliest = str(frame["session_date"].min())
            if earliest <= TRAINING_WINDOW_END:
                raise ValueError(f"RP3_EVAL_WINDOW_VIOLATION:{earliest}")
        base_design = transform_features(
            frame,
            list(self.model_preprocessor.features),
            self.model_preprocessor,
            intercept=True,
        )
        index = self.index_values(frame)
        expanded_design = np.column_stack([base_design, index])
        designs = {BASE_MODEL: base_design, EXPANDED_MODEL: expanded_design}
        out: dict[str, FloatArray] = {"index": index}
        for name, design in designs.items():
            raw = self.init_scores[name] + np.asarray(
                self.boosters[name].predict(design), dtype=np.float64
            )
            out[name] = np.asarray(
                np.exp(np.clip(raw, -EXPONENT_CLIP, EXPONENT_CLIP)), dtype=np.float64
            )
        return out


def _reproduce_index_fold(
    frame: pl.DataFrame, target: FloatArray, theta_payload: dict[str, object]
) -> tuple[FittedPreprocessor, FloatArray]:
    """Recompute the D-fold B2 preprocessor the theta was fitted against, and verify.

    The recipe is the theta artifact's own, replayed: development role, common mask,
    chronological 60/40 split, B2 design without intercept fitted on the training fold.
    Verification is against the artifact's recorded train mean and standard deviation of
    the index — if the reproduced fold statistics differed, those two numbers would not.
    """

    train_share = theta_payload["train_share"]
    assert isinstance(train_share, float)
    rank = session_rank(frame["session_date"].to_numpy())
    train, _ = chronological_split(rank, train_share=train_share)
    fitted = fit_preprocessor(frame, list(B2_FEATURES), train)
    design = transform_features(frame, list(B2_FEATURES), fitted, intercept=False)
    columns = fitted.column_names(intercept=False)
    if list(columns) != theta_payload["b2_design_columns"]:
        raise ValueError("RP3_FREEZE_INDEX_COLUMNS_MISMATCH")
    theta_values = theta_payload["theta"]
    assert isinstance(theta_values, list)
    theta = np.asarray([float(value) for value in theta_values], dtype=np.float64)
    raw_index = design @ theta
    recorded_mean = theta_payload["index_train_mean"]
    recorded_std = theta_payload["index_train_std"]
    assert isinstance(recorded_mean, float)
    assert isinstance(recorded_std, float)
    mean = float(raw_index[train].mean())
    std = float(raw_index[train].std())
    if abs(mean - recorded_mean) > 1e-9 or abs(std - recorded_std) > 1e-9:
        raise ValueError("RP3_FREEZE_INDEX_REPRODUCTION_MISMATCH")
    del target  # the index recipe never sees the target; the parameter documents that
    return fitted, theta


def freeze(
    panel_root: Path, theta_path: Path, output_dir: Path
) -> dict[str, object]:
    """Train the two program models on every pre-window row and serialize everything.

    Returns the manifest that was written. Fails closed on: a session past the training
    window, panels whose hashes differ from the ones theta names, an index that does not
    reproduce theta's recorded statistics, and a serialization that does not survive its
    own round trip.
    """

    theta_payload = json.loads(theta_path.read_text(encoding="utf-8"))
    assert isinstance(theta_payload, dict)
    if theta_payload.get("self_sha256") != _canonical_sha256(theta_payload):
        raise ValueError("RP3_FREEZE_THETA_HASH_MISMATCH")

    paths = {
        "b0_panel": panel_root / "rp2_block4_b0" / "b0_panel.parquet",
        "b1_surface_panel": panel_root / "rp2_block5_surface" / "b1_surface_panel.parquet",
        "b2_flow_panel": panel_root / "rp2_block6_flow" / "b2_flow_panel.parquet",
    }
    recorded = theta_payload["input_parquet_sha256"]
    assert isinstance(recorded, dict)
    input_hashes: dict[str, str] = {}
    for label, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"RP3_FREEZE_PANEL_MISSING:{label}:{path}")
        input_hashes[label] = _sha256_file(path)
        if label in recorded and input_hashes[label] != recorded[label]:
            raise ValueError(f"RP3_FREEZE_PANEL_MISMATCH:{label}")

    panel = load_merged_panel(
        paths["b0_panel"], paths["b1_surface_panel"], paths["b2_flow_panel"]
    )

    # The index preprocessor is fitted on the DEVELOPMENT fold, exactly as theta was.
    development = panel.filter(pl.col("role") == "D").sort(
        ["session_date", "asset", "origin_minute"]
    )
    d_target = np.asarray(development["rv30"].to_numpy(), dtype=np.float64)
    d_keep = common_evaluation_mask(development, d_target)
    development = development.filter(pl.Series(d_keep))
    index_preprocessor, theta = _reproduce_index_fold(
        development, d_target[d_keep], theta_payload
    )

    # The models train on every pre-window row across both roles.
    frame = panel.sort(["session_date", "asset", "origin_minute"])
    latest_session = _assert_training_window(frame)
    target = np.asarray(frame["rv30"].to_numpy(), dtype=np.float64)
    keep = common_evaluation_mask(frame, target)
    frame = frame.filter(pl.Series(keep))
    target = target[keep]
    sessions = session_rank(frame["session_date"].to_numpy())
    all_rows: BoolArray = np.ones(target.size, dtype=bool)

    b01 = [column for mapping in (B0_FEATURES, B1_FEATURES) for column in mapping]
    model_preprocessor = fit_preprocessor(frame, b01, all_rows)
    base_design = transform_features(frame, b01, model_preprocessor, intercept=True)
    index_design = transform_features(
        frame, list(B2_FEATURES), index_preprocessor, intercept=False
    )
    index_mean = theta_payload["index_train_mean"]
    index_std = theta_payload["index_train_std"]
    index_epsilon = theta_payload["standardisation_epsilon"]
    assert isinstance(index_mean, float)
    assert isinstance(index_std, float)
    assert isinstance(index_epsilon, float)
    index = (index_design @ theta - index_mean) / (index_std + index_epsilon)
    expanded_design = np.column_stack([base_design, index])

    parameters: dict[str, object] = {
        "metric": "None",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "verbose": -1,
        "seed": SEED,
        "deterministic": True,
        "force_row_wise": True,
    }
    log_target = np.log(np.maximum(target, VARIANCE_FLOOR))
    start = float(np.mean(log_target))

    output_dir.mkdir(parents=True, exist_ok=True)
    models: dict[str, dict[str, object]] = {}
    in_memory: dict[str, FloatArray] = {}
    for name, design in ((BASE_MODEL, base_design), (EXPANDED_MODEL, expanded_design)):
        record: dict[str, object] = {}
        booster = _fit_boosted(
            parameters,
            design,
            log_target,
            all_rows,
            sessions=sessions,
            init_score=start,
            objective=lightgbm_objective,
            metric=lightgbm_metric,
            criterion=target,
            metric_name="qlike",
            record=record,
        )
        model_path = output_dir / _MODEL_FILES[name]
        # Binary write, deliberately: text-mode writing on Windows translates \n to
        # CRLF, the recorded hash then names bytes git never stores, and every fresh
        # checkout fails verification. The bytes hashed are the bytes stored, everywhere.
        model_path.write_bytes(booster.model_to_string().encode("utf-8"))
        raw = start + np.asarray(booster.predict(design), dtype=np.float64)
        in_memory[name] = np.asarray(
            np.exp(np.clip(raw, -EXPONENT_CLIP, EXPONENT_CLIP)), dtype=np.float64
        )
        models[name] = {
            "file": _MODEL_FILES[name],
            "sha256": _sha256_file(model_path),
            "init_score": start,
            "fit_record": record,
        }

    manifest: dict[str, object] = {
        "schema": "rp3_freeze/1",
        "training_window_end": TRAINING_WINDOW_END,
        "latest_training_session": latest_session,
        "training_rows": int(target.size),
        "training_sessions": int(np.unique(sessions).size),
        "input_parquet_sha256": input_hashes,
        "theta_artifact": "artifacts/rp3/b2_index_theta.json",
        "theta_self_sha256": theta_payload["self_sha256"],
        "models": models,
        "model_preprocessor": _preprocessor_payload(model_preprocessor),
        "index": {
            "preprocessor": _preprocessor_payload(index_preprocessor),
            "design_columns": list(theta_payload["b2_design_columns"]),
            "theta": [float(value) for value in theta],
            "train_mean": index_mean,
            "train_std": index_std,
            "standardisation_epsilon": index_epsilon,
        },
        "seed": SEED,
    }
    manifest["self_sha256"] = _canonical_sha256(manifest)
    manifest_path = output_dir / MANIFEST_NAME
    manifest_path.write_bytes(
        (json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
    )

    # Round trip: what was written must predict exactly what was fitted.
    reloaded = load_frozen(output_dir)
    replayed = reloaded.predict(frame, allow_training_window=True)
    for name, values in in_memory.items():
        drift = float(np.max(np.abs(replayed[name] - values)))
        if drift > ROUND_TRIP_TOLERANCE:
            raise ValueError(f"RP3_FREEZE_ROUND_TRIP_DRIFT:{name}:{drift}")
    return manifest


def load_frozen(directory: Path) -> FrozenForecasters:
    """Reconstruct the frozen program from disk, verifying every recorded hash."""

    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"RP3_FROZEN_MANIFEST_MISSING:{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)
    if manifest.get("self_sha256") != _canonical_sha256(manifest):
        raise ValueError("RP3_FROZEN_MANIFEST_HASH_MISMATCH")

    models = manifest["models"]
    assert isinstance(models, dict)
    boosters: dict[str, lightgbm.Booster] = {}
    init_scores: dict[str, float] = {}
    for name, record in models.items():
        assert isinstance(record, dict)
        model_path = directory / str(record["file"])
        if _sha256_file(model_path) != record["sha256"]:
            raise ValueError(f"RP3_FROZEN_MODEL_HASH_MISMATCH:{name}")
        boosters[name] = lightgbm.Booster(model_str=model_path.read_text(encoding="utf-8"))
        init_score = record["init_score"]
        assert isinstance(init_score, float)
        init_scores[name] = init_score

    model_pre = manifest["model_preprocessor"]
    index_block = manifest["index"]
    assert isinstance(model_pre, dict)
    assert isinstance(index_block, dict)
    index_pre = index_block["preprocessor"]
    assert isinstance(index_pre, dict)
    theta_values = index_block["theta"]
    assert isinstance(theta_values, list)
    train_mean = index_block["train_mean"]
    train_std = index_block["train_std"]
    epsilon = index_block["standardisation_epsilon"]
    assert isinstance(train_mean, float)
    assert isinstance(train_std, float)
    assert isinstance(epsilon, float)
    return FrozenForecasters(
        manifest=manifest,
        boosters=boosters,
        init_scores=init_scores,
        model_preprocessor=_preprocessor_from_payload(model_pre),
        index_preprocessor=_preprocessor_from_payload(index_pre),
        theta=np.asarray([float(value) for value in theta_values], dtype=np.float64),
        index_mean=train_mean,
        index_std=train_std,
        index_epsilon=epsilon,
    )
