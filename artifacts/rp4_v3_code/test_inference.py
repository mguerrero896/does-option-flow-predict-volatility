"""Independent synthetic checks; no real panels, forecasts, readers or model fitting."""

import json
import math

import numpy as np
import pytest
from artifacts.rp4_v3_code import inference as module


def independent_draws(values, repetitions=199, block_length=5, seed=20260907):
    generator = np.random.default_rng(seed)
    starts = generator.integers(
        0, len(values), (repetitions, math.ceil(len(values) / block_length))
    )
    return np.array(
        [
            [
                values[(start + offset) % len(values)]
                for start in row
                for offset in range(block_length)
            ][: len(values)]
            for row in starts
        ]
    )


@pytest.mark.parametrize("statistic", ["mean", "median", "trimmed_mean_5pct"])
@pytest.mark.parametrize("alternative", ["greater", "two-sided"])
def test_bootstrap_exact_statistic_centered_null_and_plus_one(statistic, alternative):
    values = np.array(
        [
            -0.7,
            0.4,
            0.1,
            0.8,
            -0.3,
            0.9,
            0.2,
            -0.8,
            0.5,
            0.3,
            8.0,
            -3.0,
            0.1,
            0.6,
            0.2,
            -0.9,
            0.6,
            -0.4,
            0.2,
            0.1,
            0.5,
        ]
    )
    draws = independent_draws(values)

    def measure(x):
        ordered = sorted(x)
        trim = int(len(x) * 0.05)
        return (
            float(np.mean(x))
            if statistic == "mean"
            else float(np.median(x))
            if statistic == "median"
            else float(np.mean(ordered[trim:-trim] if trim else ordered))
        )

    observed = measure(values)
    boot = np.array([measure(draw) for draw in draws])
    exceed = sum(
        (x - observed >= observed)
        if alternative == "greater"
        else (abs(x - observed) >= abs(observed))
        for x in boot
    )
    actual = module.session_contrast(
        values, statistic=statistic, alternative=alternative, repetitions=199
    )
    assert actual["status"] == "COMPUTED"
    assert actual["estimate"] == pytest.approx(observed)
    assert actual["p_raw"] == pytest.approx((exceed + 1) / 200)
    assert [actual["ci_low"], actual["ci_high"]] == pytest.approx(np.quantile(boot, [0.025, 0.975]))
    assert actual["null_exceedances"] == exceed


def test_directional_bootstrap_is_not_the_fraction_of_positive_draws():
    values = np.r_[np.full(20, -0.2), np.ones(3), 5.0]
    actual = module.session_contrast(values, repetitions=499)
    reflected = module.session_contrast(-values, repetitions=499)
    boot = independent_draws(values, repetitions=499).mean(axis=1)
    sign_frequency = (np.count_nonzero(boot <= 0) + 1) / 500
    assert actual["p_raw"] != sign_frequency
    assert actual["p_raw"] < reflected["p_raw"]
    assert actual["null"] == "delta <= 0"


@pytest.mark.parametrize(
    "values", [np.ones(20), np.zeros(20), np.arange(9), np.r_[np.arange(19), np.nan]]
)
def test_insufficient_or_degenerate_session_input_is_not_evidence(values):
    result = module.session_contrast(values, repetitions=99)
    assert result["status"] == "NO VERIFICABLE"
    assert result["p_raw"] is None and result["ci_low"] is None
    assert result["N_sessions"] == len(values)


def test_median_degenerate_bootstrap_does_not_become_certain_effect():
    result = module.session_contrast(np.r_[np.ones(99), 2.0], statistic="median", repetitions=99)
    assert result["status"] == "NO VERIFICABLE"
    assert result["estimate"] == 1 and result["p_raw"] is None


def test_posterior_is_explicit_gaussian_hac_plugin_not_bootstrap_frequency():
    values = np.linspace(-1.0, 1.2, 30)
    mean = float(np.mean(values))
    centered = values - mean
    long_run = sum(x * x for x in centered) / len(values)
    for lag in range(1, 6):
        long_run += (
            2
            * (1 - lag / 6)
            * sum(centered[i] * centered[i - lag] for i in range(lag, len(values)))
            / len(values)
        )
    se = math.sqrt(long_run / len(values))
    expected = 0.5 * (1 + math.erf(mean / se / math.sqrt(2)))
    actual = module.posterior_probability_mean(values)
    assert actual["probability_positive"] == pytest.approx(expected)
    assert actual["HAC_SE"] == pytest.approx(se)
    assert actual["not_bootstrap_sign_frequency"]
    assert not actual["variance_uncertainty_integrated"]
    assert "CONDITIONAL_ASYMPTOTIC" in actual["interpretation"]
    assert module.posterior_probability_mean(np.ones(12))["probability_positive"] is None


def four_records(p_values, *, alternative="greater"):
    return [
        {
            "family": f,
            "contrast": contrast,
            "estimate": 0.1,
            "p_raw": p,
            "status": "COMPUTED",
            "statistic": "mean",
            "alternative": alternative,
        }
        for (f, contrast), p in zip(
            ((f, c[0]) for f in module.FAMILIES for c in module.CONTRASTS), p_values, strict=True
        )
    ]


def test_h2_cannot_be_promoted_after_failed_h1_and_all_families_are_required():
    result = module.family_fixed_sequence(four_records([0.2, 0.0001, 0.01, 0.01]))
    second = result["contrasts"][1]
    assert second["hypothesis_status"] == "NOT_TESTED"
    assert second["p_raw"] == 0.0001 and second["p_for_decision"] is None
    assert second["nominal_p_role"] == "NO_PROMOTABLE"
    assert not result["global_joint_reject"] and not result["any_family_claim_allowed"]
    assert result["families"]["lightgbm_qlike"]["both_rejected"]


def test_sequence_alpha_boundary_sign_and_primary_secondary_scope():
    rows = four_records([0.05] * 4)
    assert module.family_fixed_sequence(rows)["global_joint_reject"]
    rows[0]["estimate"] = -0.1
    assert not module.family_fixed_sequence(rows)["global_joint_reject"]
    with pytest.raises(ValueError, match="INVALID_SCOPE"):
        module.family_fixed_sequence(rows, endpoint="jump_auc")
    result = module.family_fixed_sequence(rows, endpoint="jump_auc", primary=False)
    assert result["scope"] == "SECONDARY_ENDPOINT_JOINT"
    with pytest.raises(ValueError, match="FOUR_FAMILY"):
        module.family_fixed_sequence(rows[:-1])


def test_holm_secondary_retains_four_slots_and_does_not_replace_primary():
    rows = four_records([0.01, 0.02, 0.2, None], alternative="two-sided")
    rows[-1].update(status="NO VERIFICABLE", estimate=None)
    corrected = module.holm_four(rows)
    assert [r["p_holm"] for r in corrected] == [0.04, 0.06, 0.4, None]
    assert corrected[-1]["holm_unavailable_treated_as_one"]
    assert all(r["inference_role"] == "SECONDARY" for r in corrected)
    with pytest.raises(ValueError, match="DIRECTIONAL"):
        module.family_fixed_sequence(rows)


def test_secondary_auc_cannot_rescue_primary_qlike_by_omitting_an_argument():
    rows = four_records([0.001] * 4)
    for row in rows:
        row.update(endpoint="jump_auc", inference_role="SECONDARY")
    with pytest.raises(ValueError, match="SECONDARY_INPUT"):
        module.family_fixed_sequence(rows)
    assert module.family_fixed_sequence(rows, primary=False, endpoint="jump_auc")[
        "global_joint_reject"
    ]


def test_nonfinite_statistics_remain_json_safe_and_missing_sessions_are_rejected():
    for result in (
        module.session_contrast([np.inf] * 10),
        module.session_contrast([1e308] * 10),
        module.posterior_probability_mean([1e308] * 10),
    ):
        assert result["status"] == "NO VERIFICABLE"
        json.dumps(result, allow_nan=False)
    with pytest.raises(ValueError, match="SESSION_LABEL"):
        module.SessionAUC.from_predictions([0, 1], [0.1, 0.2], [None, "2026-08-03"])


def test_quantile_pinball_loss_uses_log_units_and_correct_tail_sign():
    result = module.quantile_loss_log_rv([-3, -2, -1], [-2, -2, -2])
    assert result == pytest.approx([0.1, 0, 0.9])
    with pytest.raises(ValueError, match="NONFINITE"):
        module.quantile_loss_log_rv([np.nan], [0])


def pairwise_auc(labels, predictions):
    positive = predictions[labels == 1]
    negative = predictions[labels == 0]
    if not len(positive) or not len(negative):
        return np.nan
    return sum(float(p > n) + 0.5 * float(p == n) for p in positive for n in negative) / (
        len(positive) * len(negative)
    )


@pytest.mark.parametrize("chunk", [1, 2, 1024])
def test_auc_pair_matrix_exact_for_ties_and_repeated_sessions(chunk):
    labels = np.array([1, 0, 1, 0, 0, 1, 0, 1])
    scores = np.array([0.3, 0.3, 0.2, 0.4, 0.8, 0.8, 0.1, 0.4])
    sessions = np.array([0, 0, 1, 1, 2, 2, 3, 3])
    matrix = module.SessionAUC.from_predictions(labels, scores, sessions, group_chunk_size=chunk)
    multiplicities = np.array([[1, 1, 1, 1], [3, 0, 2, 1], [0, 2, 1, 0], [1, 0, 0, 0]])
    got = matrix.evaluate(multiplicities, batch_size=1)
    for weights, observed in zip(multiplicities, got, strict=True):
        indices = np.repeat(np.arange(len(labels)), weights[sessions])
        assert observed == pytest.approx(pairwise_auc(labels[indices], scores[indices]))
    assert matrix.pair_counts.sum() / (
        labels.sum() * (len(labels) - labels.sum())
    ) == pytest.approx(pairwise_auc(labels, scores))


def auc_fixture():
    sessions = np.repeat(np.arange(12), 4)
    labels = np.tile([0, 1, 0, 1], 12)
    random = np.random.default_rng(420)
    return (
        labels,
        {
            "B0": random.normal(size=48),
            "B1": random.normal(size=48) + labels * 0.4,
            "B2": random.normal(size=48) + labels * 0.6,
        },
        sessions,
    )


def test_pooled_auc_bootstrap_exact_against_literal_session_duplication():
    labels, predictions, sessions = auc_fixture()
    result = module.pooled_auc_inference(
        labels, predictions, sessions, family="lightgbm_qlike", repetitions=99
    )
    indices = independent_draws(np.arange(12), repetitions=99).astype(int)
    expected = {}
    for name, score in predictions.items():
        bootstrap = []
        for draw in indices:
            rows = np.concatenate([np.flatnonzero(sessions == d) for d in draw])
            bootstrap.append(pairwise_auc(labels[rows], score[rows]))
        expected[name] = np.array(bootstrap)
        assert result["auc"][name]["estimate"] == pytest.approx(pairwise_auc(labels, score))
        assert [result["auc"][name]["ci_low"], result["auc"][name]["ci_high"]] == pytest.approx(
            np.quantile(bootstrap, [0.025, 0.975])
        )
    for actual, (_, base, expanded) in zip(result["contrasts"], module.CONTRASTS, strict=True):
        delta = pairwise_auc(labels, predictions[expanded]) - pairwise_auc(
            labels, predictions[base]
        )
        values = expected[expanded] - expected[base]
        p = (np.count_nonzero(values - delta >= delta) + 1) / 100
        assert actual["estimate"] == pytest.approx(delta)
        assert actual["p_raw"] == pytest.approx(p)
    assert result["invalid_class_resamples"] == 0


def test_auc_classless_draws_are_counted_without_reroll_or_silent_conditioning():
    sessions = np.repeat(np.arange(12), 2)
    labels = np.zeros(24)
    labels[0] = 1
    predictions = {name: np.linspace(0, 1, 24) + i * labels for i, name in enumerate(module.SETS)}
    result = module.pooled_auc_inference(
        labels, predictions, sessions, family="lightgbm_qlike", repetitions=99
    )
    expected = sum(0 not in draw for draw in independent_draws(np.arange(12), repetitions=99))
    assert result["invalid_class_resamples"] == expected > 0
    assert result["status"] == "NO VERIFICABLE"
    assert all(r["estimate"] is not None and r["ci_low"] is None for r in result["auc"].values())
    assert all(r["p_raw"] is None for r in result["contrasts"])
    original = module.pooled_auc_inference(
        np.zeros(24), predictions, sessions, family="lightgbm_qlike", repetitions=99
    )
    assert all(r["estimate"] is None for r in original["auc"].values())


def test_auc_rejects_invalid_scores_and_multiplicities_instead_of_changing_mask():
    with pytest.raises(ValueError, match="INVALID_INPUT"):
        module.SessionAUC.from_predictions([0, 1], [0.1, np.nan], [0, 0])
    matrix = module.SessionAUC.from_predictions([0, 1], [0.1, 0.2], [0, 0])
    with pytest.raises(ValueError, match="MULTIPLICITIES"):
        matrix.evaluate([0.5])
    assert np.isnan(matrix.evaluate([0])[0])
