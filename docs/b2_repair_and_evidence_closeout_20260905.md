# B2 history repair and historical sensitivity - 5 September 2026

This note presents the already evaluated B2 repair and its limits. The current
integration preserves those records; it does not repeat their evaluation. RP4 v4
remains the current headline. The source branch retains the original historical
closeout, including its operational record and separate HARQ discussion.

## 1. Repair and input validation

`build_b2v2_from_activity` excludes ineligible history before calculating location
and scale, including the asset-level fallback. It preserves original keys, a
60-prior-session window, a minimum of 20 eligible sessions and 80% history coverage.
Invalid input is not converted into zero.

`build_target_blind_common_panel_v22.build_panel` supplies eligibility for the
primary variant to the normalizer. The v2.3 and v2.4 builders delegate to that
producer. Existing synthetic checks cover the real builder and asset fallback,
including a 1e9 change confined to an excluded row.

The historical caller review identified that source-time, legacy and multiscale
paths already supplied the sidecar; independent replication excluded incident
sessions before normalization. B1v3 uses compact row-level transformations rather
than this historical normalization. Its models and missingness are unchanged.

A subsequent input-validation correction rejects nulls explicitly in
`add_compact_b2_features`, alongside negatives and non-finite values, using
`B2_RAW_FEATURE_VALUES_INVALID`. Valid zeros remain valid. The historical null
reproduction produced nine finite features and `b2v2_complete=true` from invalid
premium inputs; this established a producer defect, not its occurrence in every
real campaign. No missing values are imputed.

## 2. Recorded feature impact

Source: [impact and hashes](../artifacts/b2_history_repair_v1/feature_impact.json).
The historical feature stage exactly reproduced the published predictor values
before comparison with the repair; it read no targets.

| Universe | Complete before/after | Origins with changed features | Changed cells |
|---|---:|---:|---:|
| B2, 180 sessions and 77,328 total origins | 68,237 / 68,237 | 27,153 | 244,377 |
| Published common predictor panel, 159 sessions | 62,266 / 62,266 | 24,604 | 221,436 |

The repair excludes 451 ineligible history rows. Its effect is measured jointly,
not attributed individually to each row. In the common panel,
`24,604 / 62,266 * 100 = 39.51%` of origins change. Every complete row is retained;
there was no selection by result sign.

The historical follow-up recorded zero null, non-finite or negative values in the
11 raw columns across 77,328 rows and 180 files. Its input digest matched the
feature-impact record before and after inspection. That separate raw-value audit
is not included here and was not repeated by this integration. Its stated scope
was the exact repair inputs; it did not certify other campaigns or their temporal
provenance. The raw-value guard therefore adds no measured gain to these results.

## 3. Recorded retrospective sensitivity

Sources: [protocol](../artifacts/b2_history_repair_v1/evaluation_protocol.json)
and [result](../artifacts/b2_history_repair_v1/evaluation_result.json).

The historical comparison reused exposed targets, archived Gamma and LightGBM
parameters and the two original folds. There was no hyperparameter search. It
retained 62,254 rows with valid targets and generated 149,688 forecasts per arm.
The 12 excluded origins had incomplete targets in the original result; the repair
introduced no new target exclusions.

The historical replay reproduced forecasts, QLIKE, absolute errors and squared
errors with maximum error **zero**. B0 and B1 also remained identical between
arms, with maximum error **zero**. These are recorded receipt controls; checking
them during integration is not a second experimental execution.

The following comparison uses only the 32 historical holdout sessions from
2026-02-05 to 2026-03-23, excluding the validation fold:

| Model | QLIKE gain B1 over B0 | Previous B2 gain over B1 | Repaired B2 gain over B1 |
|---|---:|---:|---:|
| Gamma | +0.008171247318 | -0.003126621051 | -0.002205552554 |
| LightGBM | +0.004175806123 | +0.001368014098 | +0.001055171107 |

Gain is parent-model loss minus child-model loss, averaged by origin. The JSON
also retains session averages, assets, training-defined regimes and four
chronological blocks. Validation and holdout are not pooled into a new replication.

The correction reduces Gamma's QLIKE deterioration without changing its sign.
LightGBM retains a descriptive aggregate B2 > B1 > B0 ordering, with a smaller B2
gain. Both B2 models retain negative blocks and regimes. B2 MAE and RMSE worsen
slightly against the previous B2 in both models, while remaining better than B1.
The repair did not improve every metric or establish general robustness.

## 4. Exposure, claim boundary and reproduction limits

The [exposure audit](pit_v22_claims_and_limitations_v3.md) records
`PASS_RETROSPECTIVE_EXPOSURE_VERIFIED`: all 32 holdout sessions had already
appeared in C3 and RP2 development calendars. The PIT v2.2 result is retrospective
and descriptive. Signed definitions and original estimates are preserved; they
do not constitute independent confirmation. Changing a cutoff or permitting
reuse cannot remove information previously used to select a procedure.

Overlapping campaigns are not added together or counted as independent
replications. Historical client availability remains unproven by `created_at`
or `sip_timestamp`; comparing aggregate alerts with individual trades does not
identify revisions or backfill. This repair does not resolve those provenance
limits. Separate HARQ comparisons involve different models and samples, so no
B2 repair benefit is transferred to them.

The impact, protocol and result JSON files are preserved byte for byte.
`feature_stage_source.py` preserves the historical impact producer source.
Runtime hashes in the protocol describe the environment used for the historical
evaluation. The current `phase6_evaluation.py` differs from that runtime;
integration does not establish an identical replay in today's environment.
A branch SHA alone does not reconstruct historical uncommitted runtime state.
This reproduction limitation is not resolved by rewriting receipts or copying
unverified dependencies. Historical evidence must not be deleted to force replay.

This integration does not refit models or read new outcomes. Frozen estimates,
intervals, p-values, custody records and the separate sensitivity remain intact.
Historical focused-test claims do not establish that today's full suite passes.

Historical sensitivity alpha spent: **0**; provider requests: **0**.
Different signs across models and regimes do not establish a globally robust
B2 > B1 > B0 hierarchy or profitability. Forecasting RV30 and measuring the
incremental contribution of options are distinct questions. `RESEARCH_ONLY`,
`NOT INVESTMENT ADVICE`, and `capital_go=false` remain binding.
