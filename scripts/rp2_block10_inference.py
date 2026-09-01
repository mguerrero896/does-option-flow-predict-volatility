"""Block 10 - the inference the program says is still missing.

Clark-West for the nested contrasts, Giacomini-White for conditional predictive ability,
and Hansen SPA / White Reality Check over the whole family of model x information-set
combinations, so that the best of many transformations has to survive its own selection.

Development and validation are retrospective exploratory analyses at alpha 0.05. The
sequential budget is recorded only as a future-campaign contract and post-hoc sensitivity;
it is not relabelled as preregistered confirmation.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

from mds650.b1v3_confirmation import canonical_sha256
from mds650.metrics import qlike_losses
from mds650.rp2.feature_registry import assert_segment_coverage, describe_coverage
from mds650.rp2.inference import (
    DEFAULT_ALPHA,
    DEFAULT_POWER,
    DEFAULT_SEED,
    SPA_REPETITIONS,
    aggregate_by_session,
    clark_west_terms,
    clustered_mean_test,
    hansen_spa,
    model_family_of,
    session_contrast,
    session_giacomini_white,
)
from mds650.rp2.ladder import (
    BOOSTED_LADDER,
    PRIMARY_MODELS,
    assert_primary_models,
    canonical_float_array_sha256,
    fit_ladder_model,
)
from mds650.rp2.panel import (
    B0_FEATURES,
    B1_FEATURES,
    B2_FEATURES,
    CORE_SETS,
    DEFAULT_TRAIN_SHARE,
    build_design,
    chronological_split,
    common_evaluation_mask,
    describe_information_set,
    lift_mask,
    load_merged_panel,
    mask_sha256,
    panel_paths,
    session_rank,
)
from mds650.rp2.pbo import MIN_CANDIDATES, probability_of_backtest_overfitting
from mds650.rp2.preprocessing import describe_preprocessor, fold_design

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "rp2_block10_inference"

INFORMATION_SETS: dict[str, list[dict[str, str]]] = {
    "B0": [B0_FEATURES],
    "B0+B1": [B0_FEATURES, B1_FEATURES],
    "B0+B2": [B0_FEATURES, B2_FEATURES],
    "B0+B1+B2": [B0_FEATURES, B1_FEATURES, B2_FEATURES],
}
NESTED_PAIRS: dict[str, tuple[str, str]] = {
    "b1_over_b0": ("B0", "B0+B1"),
    "b2_over_b1": ("B0+B1", "B0+B1+B2"),
    "b2_over_b0": ("B0", "B0+B2"),
    "total_over_b0": ("B0", "B0+B1+B2"),
}
#: The families the research contract decides on. `log_ols` and `lightgbm` remain
#: available through --models as robustness, but a default run reports the three
#: families the conclusions are read off.
DEFAULT_MODELS: tuple[str, ...] = PRIMARY_MODELS
#: Families whose restricted form really is a parameter restriction of the unrestricted
#: one, which is the precondition Clark-West is derived under.
NESTED_LINEAR_FAMILIES: frozenset[str] = frozenset({"log_ols", "ridge_log"})
#: Decision 64 alpha spending, alpha_k = 0.05 / (k (k+1)); this program is one further look.
ALPHA_SPENDING_STEP = 3

type FloatArray = npt.NDArray[np.float64]


def alpha_budget(step: int) -> float:
    return 0.05 / (step * (step + 1))


def session_loss_series(
    base_losses: FloatArray,
    expanded_losses: FloatArray,
    sessions: npt.NDArray[np.int64],
    session_dates: npt.NDArray[np.str_],
    *,
    expected_estimate: float,
) -> list[dict[str, object]]:
    """Persist the exact session means behind one registered flow estimate."""

    if base_losses.shape != expanded_losses.shape or base_losses.shape != sessions.shape:
        raise ValueError("RP2_SESSION_LOSS_SHAPE_MISMATCH")
    if session_dates.shape != sessions.shape:
        raise ValueError("RP2_SESSION_LOSS_DATE_SHAPE_MISMATCH")
    if not np.isfinite(base_losses).all() or not np.isfinite(expanded_losses).all():
        raise ValueError("RP2_SESSION_LOSS_NONFINITE")
    base, labels = aggregate_by_session(base_losses, sessions)
    expanded, expanded_labels = aggregate_by_session(expanded_losses, sessions)
    difference, difference_labels = aggregate_by_session(base_losses - expanded_losses, sessions)
    if not np.array_equal(labels, expanded_labels) or not np.array_equal(
        labels, difference_labels
    ):
        raise ValueError("RP2_SESSION_LOSS_LABEL_MISMATCH")
    dates: list[str] = []
    origins: list[int] = []
    for label in labels:
        selected = session_dates[sessions == label]
        unique = np.unique(selected)
        if unique.size != 1:
            raise ValueError("RP2_SESSION_LOSS_DATE_LABEL_MISMATCH")
        dates.append(str(unique[0]))
        origins.append(int(selected.size))
    if dates != sorted(set(dates)):
        raise ValueError("RP2_SESSION_LOSS_DATES_NOT_STRICTLY_ORDERED")
    if not np.isclose(float(difference.mean()), expected_estimate, rtol=0.0, atol=1e-15):
        raise ValueError("RP2_SESSION_LOSS_ESTIMATE_MISMATCH")
    return [
        {
            "session_date": date,
            "origins": count,
            "loss_without_flow": float(without),
            "loss_with_flow": float(with_flow),
            "delta_loss": float(delta),
        }
        for date, count, without, with_flow, delta in zip(
            dates, origins, base, expanded, difference, strict=True
        )
    ]


def run_role(
    panel: pl.DataFrame, *, role: str, train_share: float, models: Sequence[str]
) -> dict[str, object]:
    frame = panel.filter(pl.col("role") == role).sort(["session_date", "asset", "origin_minute"])
    target = np.asarray(frame["rv30"].to_numpy(), dtype=np.float64)
    # build_design still fails closed on a registered feature the panel does not carry; its
    # matrix is discarded, because the design a fold fits is built by the preprocessor from
    # that fold's own training statistics.
    resolved: dict[str, tuple[str, ...]] = {}
    features: dict[str, list[str]] = {}
    for name, maps in INFORMATION_SETS.items():
        _, resolved[name] = build_design(frame, maps)
        features[name] = [column for mapping in maps for column in mapping]
    keep = common_evaluation_mask(frame, target)
    information_sets = {
        name: describe_information_set((name,), resolved[name], keep) for name in INFORMATION_SETS
    }
    if int(keep.sum()) < 2000:
        return {
            "status": "INSUFFICIENT_ROWS",
            "rows": int(keep.sum()),
            "information_sets": information_sets,
        }

    role_frame = frame
    frame = frame.filter(pl.Series(keep))
    target = target[keep]
    sessions_rank = session_rank(frame["session_date"].to_numpy())
    train, test = chronological_split(sessions_rank, train_share=train_share)
    # The floor holds on the panel and on this role; it also has to hold on the two
    # segments this run fits and scores, which is where a held-out tail with a gap in it
    # would otherwise become a result. The masks are lifted back onto the unfiltered role
    # frame: checking them on the frame the common mask has already pruned would be
    # checking that the rows which survived are the rows which survived.
    assert_segment_coverage(
        role_frame,
        {"train": lift_mask(keep, train), "test": lift_mask(keep, test)},
        *CORE_SETS.values(),
    )
    # One design per information set, imputed and scaled from this fold's training rows.
    designs: dict[str, FloatArray] = {}
    preprocessors: dict[str, object] = {}
    for name in INFORMATION_SETS:
        designs[name], _, fitted = fold_design(frame, features[name], train)
        preprocessors[name] = describe_preprocessor(fitted)
    information_sets = {
        name: describe_information_set((name,), resolved[name], lift_mask(keep, test))
        for name in INFORMATION_SETS
    }
    clusters = sessions_rank[test]
    session_dates = np.asarray(frame["session_date"].to_numpy()[test], dtype=np.str_)
    # The rows every contrast below is scored on, and the digest that identifies them.
    evaluated_mask_sha256 = mask_sha256(lift_mask(keep, test))
    log_target = np.log(np.maximum(target, 1e-12))

    # Conditioning variables for Giacomini-White: ex-ante observable state, taken from the
    # fold-local design rather than raw. Two of the three are registered B0 features, and a
    # raw NaN would be dropped inside the test by its own finite filter — so the conditional
    # statistic would be computed on a feature-selected subsample while the unconditional
    # tests beside it used the recorded common mask. The origin minute is exact and needs no
    # imputation, but is standardised with the same fold statistics for comparability.
    conditioner_features = ["rv_back_30", "dollar_volume_30", "minutes_since_open"]
    conditioners, _, conditioner_fitted = fold_design(
        frame, conditioner_features, train, intercept=False
    )
    conditioners = conditioners[test]
    preprocessors["giacomini_white_conditioners"] = describe_preprocessor(conditioner_fitted)

    results: dict[str, object] = {
        "status": "MEASURED",
        "preprocessing": preprocessors,
        "rows": int(keep.sum()),
        "train_share": train_share,
        "test_rows": int(test.sum()),
        "clusters": int(np.unique(clusters).size),
        # The rows every contrast in this role was scored on. The ladder records the same
        # digest for the same role; the runner compares them, and a divergence means the
        # two producers evaluated different samples.
        "evaluation_mask_sha256": evaluated_mask_sha256,
        "information_sets": information_sets,
    }
    all_losses: dict[str, FloatArray] = {}
    per_model: dict[str, object] = {}
    model_provenance: dict[str, object] = {}
    flow_loss_models: dict[str, object] = {}
    for model_name in models:
        forecasts: dict[str, FloatArray] = {}
        losses: dict[str, FloatArray] = {}
        forecast_hashes: dict[str, str] = {}
        loss_hashes: dict[str, str] = {}
        boosting: dict[str, object] = {}
        for set_name in INFORMATION_SETS:
            record: dict[str, object] | None = (
                {} if model_name in BOOSTED_LADDER else None
            )
            forecast = fit_ladder_model(
                model_name,
                designs[set_name],
                target,
                train,
                sessions=sessions_rank,
                record=record,
            )
            forecasts[set_name] = forecast[test]
            losses[set_name] = qlike_losses(target[test], forecast[test])
            forecast_hashes[set_name] = canonical_float_array_sha256(forecasts[set_name])
            loss_hashes[set_name] = canonical_float_array_sha256(losses[set_name])
            if record is not None:
                boosting[set_name] = record
            all_losses[f"{model_name}|{set_name}"] = losses[set_name]
        block: dict[str, object] = {}
        for label, (base, expanded) in NESTED_PAIRS.items():
            # Clark-West is defined on squared error, so it runs on the log scale where
            # the nested models are actually linear in their extra parameters.
            # Clark-West is derived for a linear model whose restricted form is a
            # parameter restriction of the unrestricted one. A boosted tree on a larger
            # feature set is a different function class, not a nested restriction, so the
            # adjustment is not applied there.
            nested_linear = model_name in NESTED_LINEAR_FAMILIES
            if nested_linear:
                terms = clark_west_terms(
                    log_target[test],
                    np.log(np.maximum(forecasts[base], 1e-12)),
                    np.log(np.maximum(forecasts[expanded], 1e-12)),
                    nested_linear=True,
                )
                cw = clustered_mean_test(terms, clusters)
            else:
                cw = None
            difference = losses[base] - losses[expanded]
            gw = session_giacomini_white(difference, conditioners, clusters)
            contrast = session_contrast(
                losses[base],
                losses[expanded],
                clusters,
                model_family=model_name,
                base_information_set=base,
                expanded_information_set=expanded,
                common_mask_sha256=evaluated_mask_sha256,
                alpha=DEFAULT_ALPHA,
                power=DEFAULT_POWER,
            )
            record = contrast.as_record()
            record.update(
                {
                    "clark_west_applicable": nested_linear,
                    "clark_west_mean": cw.mean if cw else None,
                    "clark_west_t": cw.t_statistic if cw else None,
                    "clark_west_p_one_sided": cw.p_value_one_sided if cw else None,
                    "giacomini_white_wald": gw.wald,
                    "giacomini_white_p": gw.p_value,
                    "equivalence_interpretation": (
                        "EXPLORATORY_BOOTSTRAP_CI_WITHIN_MARGIN_NOT_TOST"
                    ),
                }
            )
            block[label] = record
        per_model[model_name] = block
        flow_record = block["b2_over_b1"]
        assert isinstance(flow_record, dict)
        flow_loss_models[model_name] = session_loss_series(
            losses["B0+B1"],
            losses["B0+B1+B2"],
            clusters,
            session_dates,
            expected_estimate=float(flow_record["estimate"]),
        )
        model_provenance[model_name] = {
            "forecast_sha256": forecast_hashes,
            "loss_sha256": loss_hashes,
            "boosting_rounds": boosting,
        }
    results["nested_tests"] = per_model
    results["model_provenance"] = model_provenance
    results["flow_loss_series"] = {
        "schema_version": 1,
        "unit": "session_mean_qlike",
        "base_information_set": "B0+B1",
        "expanded_information_set": "B0+B1+B2",
        "evaluation_mask_sha256": evaluated_mask_sha256,
        "models": flow_loss_models,
    }

    # SPA / Reality Check, one per family: each family's own B0 is the benchmark and its
    # own expansions are the candidates. Racing `log_ols|B0` against `lightgbm|B0+B1+B2`
    # would confound the estimator with the information set, which is the one thing these
    # contrasts exist to separate.
    # Two benchmarks per family, because the programme asks two questions. Against B0 the
    # candidates answer "does anything beyond the baseline help"; against B0+B1 the single
    # candidate answers the frozen dB2|B1 question, which a B0 benchmark cannot: there,
    # B0+B1+B2 is credited with B1's increment as well.
    spa_by_family: dict[str, object] = {}
    for model_name in models:
        family: dict[str, object] = {}
        for benchmark_set, candidate_sets in (
            ("B0", ("B0+B1", "B0+B2", "B0+B1+B2")),
            ("B0+B1", ("B0+B1+B2",)),
        ):
            candidates = {
                f"{model_name}|{name}": all_losses[f"{model_name}|{name}"]
                for name in candidate_sets
                if f"{model_name}|{name}" in all_losses
            }
            if not candidates:
                continue
            spa = hansen_spa(
                all_losses[f"{model_name}|{benchmark_set}"],
                candidates,
                sessions=clusters,
                benchmark_name=f"{model_name}|{benchmark_set}",
                repetitions=SPA_REPETITIONS,
                seed=DEFAULT_SEED,
            )
            family[benchmark_set] = {
                "benchmark": f"{model_name}|{benchmark_set}",
                "best_model": spa.best_model,
                "best_mean_delta_qlike": spa.best_mean_difference,
                "spa_p_value": spa.spa_p_value,
                "reality_check_p_value": spa.reality_check_p_value,
                "candidates": spa.candidates,
                "sessions": spa.observations,
            }
        spa_by_family[model_name] = family
    results["superior_predictive_ability"] = spa_by_family

    # Probability of backtest overfitting. `docs/research_program_v2.md` lists it among the
    # metrics this programme reports and nothing computed it until now. SPA asks whether any
    # candidate genuinely beats its benchmark; PBO asks the complementary question a reader
    # of a multi-cell search asks first -- if I keep the cell that looked best, how often is
    # that cell below median out of sample.
    #
    # The primary measurement is within family, for the reason `assert_family_matched`
    # states: a family against itself across information sets isolates the information,
    # while a family against another family confounds estimator with information. The
    # all-cell figure is reported beside it and labelled, because the programme does name a
    # headline across families and that selection carries its own risk.
    overfitting: dict[str, object] = {}
    for model_name in models:
        family_losses = {
            name: losses
            for name, losses in all_losses.items()
            if model_family_of(name) == model_name
        }
        if len(family_losses) >= MIN_CANDIDATES:
            overfitting[model_name] = probability_of_backtest_overfitting(
                family_losses, clusters
            ).as_dict()
    if len(all_losses) >= MIN_CANDIDATES:
        confounded = probability_of_backtest_overfitting(all_losses, clusters).as_dict()
        confounded["note"] = (
            "Every model family and information set in one universe. This confounds "
            "estimator with information set, which assert_family_matched forbids for SPA; "
            "it is reported because the programme selects a headline across families."
        )
        overfitting["all_cells_confounded"] = confounded
    results["backtest_overfitting"] = overfitting
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    # A rebuild writes its panels into its own run directory; without this the
    # block would silently read the previous run's panels and label the result
    # with the new run id.
    parser.add_argument("--panel-root", type=Path, default=None)
    parser.add_argument("--train-share", type=float, default=DEFAULT_TRAIN_SHARE)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    args = parser.parse_args(argv)

    models = tuple(name.strip() for name in str(args.models).split(",") if name.strip())
    assert_primary_models(models)
    panels = panel_paths(args.panel_root)
    panel = load_merged_panel(panels["b0"], panels["b1"], panels["b2"])
    document: dict[str, object] = {
        # Which frozen sets were fitted, how complete they were, and the hash of the
        # registry that decided them. Without it an artifact records a design width and
        # nothing a reader can check that width against.
        "feature_registry": describe_coverage(panel, *CORE_SETS.values()),
        "block": 10,
        "program": "docs/research_program_v2.md",
        "label": "EXPLORATORY_MECHANISM_DISCOVERY",
        "models": list(models),
        "inference_alpha": DEFAULT_ALPHA,
        "inference_power": DEFAULT_POWER,
        "future_alpha_spending_step": ALPHA_SPENDING_STEP,
        "future_alpha_budget": alpha_budget(ALPHA_SPENDING_STEP),
        "alpha_budget_scope": "FUTURE_CAMPAIGNS_ONLY_POST_HOC_SENSITIVITY_HERE",
    }
    for role in ("D", "V"):
        document[role] = run_role(panel, role=role, train_share=args.train_share, models=models)
    document["inference_sha256"] = canonical_sha256(document)
    document["generated_at_utc"] = datetime.now(UTC).isoformat()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "inference.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"alpha budget at step {ALPHA_SPENDING_STEP}: {alpha_budget(ALPHA_SPENDING_STEP):.5f}")
    for role in ("D", "V"):
        block = document[role]
        assert isinstance(block, dict)
        print(f"=== role {role}: {block.get('status')} clusters={block.get('clusters')} ===")
        nested = block.get("nested_tests")
        if isinstance(nested, dict):
            for model_name, pairs in nested.items():
                assert isinstance(pairs, dict)
                for label, stats in pairs.items():
                    assert isinstance(stats, dict)
                    cw_text = (
                        f"CW t={stats['clark_west_t']:+6.2f} "
                        f"p={stats['clark_west_p_one_sided']:.4f}"
                        if stats.get("clark_west_applicable")
                        else "CW n/a (not nested linear)"
                    )
                    print(
                        f"  {model_name:<11} {label:<14} {cw_text}  "
                        f"GW p={stats['giacomini_white_p']:.4f}  "
                        f"session dQLIKE={stats['estimate']:+.5f} "
                        f"p={stats['p_value']:.4f} n={stats['sessions']:d} "
                        f"mde={stats['mde']:.5f}"
                    )
        spa_by_family = block.get("superior_predictive_ability")
        if isinstance(spa_by_family, dict):
            for family, by_benchmark in spa_by_family.items():
                assert isinstance(by_benchmark, dict)
                for benchmark_set, spa in by_benchmark.items():
                    assert isinstance(spa, dict)
                    print(
                        f"  SPA {family:<15} vs {benchmark_set:<6} "
                        f"best={spa['best_model']:<26} "
                        f"delta={spa['best_mean_delta_qlike']:+.5f} "
                        f"SPA p={spa['spa_p_value']:.4f} "
                        f"RC p={spa['reality_check_p_value']:.4f} n={spa['sessions']:d}"
                    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
