# Threats-to-validity matrix (current at 2026-09-02)

This matrix follows `data/CANONICAL_STATE.json`. Historical gate documents cannot
override it. The PIT v2.2 successor-v2 result is
`CURRENT_RETROSPECTIVE_REMEASUREMENT_EXPLORATORY_DESCRIPTIVE`: its immutable outputs are
custody-valid, but the exposed 32-session holdout cannot serve as confirmatory evidence or
authorize a global edge or capital claim. The RP2 D/V bundle remains
`HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM`. Phase 8 consumed its sole exploratory read
(`sealed_cohorts_read=1`); Phase 9 remains sealed and unread
(`sealed_cohorts_read=0`).

| # | Threat | Evidence record | Mitigation | Residual risk |
|---|---|---|---|---|
| 1 | Adaptive campaigns, multiplicity and holdout exposure | D/V were reused for selection and recalibration; retrospective ordering was not preregistered. `successor_holdout_exposure_v1.json` is `PASS_RETROSPECTIVE_EXPOSURE_VERIFIED`: all 32 successor-holdout sessions intersect both C3 and RP2-v3 D. | The successor is `RETROSPECTIVE_REMEASUREMENT_UNDER_PIT_V22` and `EXPLORATORY_DESCRIPTIVE`; `one-shot` is limited to access custody. D/V and the consumed Phase 8 bridge are exploratory; α=0.00417 is only a non-binding post-hoc sensitivity and a future-campaign budget. | No retrospective correction or Phase 8 outcome can become confirmation. The successor is outside the confirmatory alpha sequence; Phase 9 retains its separate read gate. |
| 2 | Model-family dependence | Gamma, Ridge and LightGBM differ in sign and precision across D/V | Same information-set masks and session-aware model selection; family-specific reporting | No universal B1/B2 claim is supported |
| 3 | Calibration versus information | QLIKE rewards calibration; historical effects changed after recalibration and producer repairs | The current successor uses frozen QLIKE contrasts and reports MAE/RMSE only secondarily; Gamma B1a survives Holm but remains below its MDE | QLIKE improvement may reflect calibration rather than an economic mechanism |
| 4 | Multiple model/target search | Historical extensions searched many cells | Family-matched SPA/Reality Check and explicit exploratory labels | Data-dependent search remains a limit; no confirmatory discovery is claimed |
| 5 | Serial dependence and interval calibration | Five-minute origins overlap; the 0.784 empirical coverage measurement against nominal 0.95 belongs to the superseded RP2 run | The successor uses a paired whole-session bootstrap over 32 holdout sessions; the historical coverage diagnostic is not promoted | Thirty-two clusters remain a short sample and intervals may still undercover |
| 6 | Target choice | The historical D/V diagnostic favors RV60 in D and RV30 in V | RV30 remains the owner-frozen primary; divergence is disclosed | Target preference is partition-dependent |
| 7 | Point-in-time availability | Source timestamps are available, but UW `created_at` and Massive SIP time do not prove historical client receipt | Claims are `PROXY_ONLY` / source-time PIT under documented assumptions; preflight fails closed | Historical client availability is not proven |
| 8 | Licensed-data reproducibility | Granular inputs cannot be redistributed | Public hashes, schemas, manifests and controlled access; Tier 2 remains separate from hermetic CI | Independent reruns require approved access and provider entitlements |
| 9 | Event/regime composition | The successor retains descriptive stability by asset, session segment and volatility regime; timing-sensitivity forecasts were not evaluated | Report the registered global contrasts as authority and keep subgroup cells descriptive | Timing robustness and transport across regimes remain unestablished |
| 10 | Microstructure proxy error | RV30 is trade-price based and option-flow variables are provider-derived proxies | Noise sensitivity and source-time contracts are documented | Other proxies and feeds may yield different results |
| 11 | Common-complete selection | Information sets and incomplete RV30 horizons can drop origins | The pre-OOS rule uses predictor-complete intersect target-complete: 62,266 predictor-complete origins became 62,254 eligible, with no imputation or provider substitution | Results apply to the eligible complete-case population, not every market interval |
| 12 | Narrow universe | Six liquid mega-cap equities | Scope is stated; SPY/QQQ are controls, not additional outcomes | No broad cross-sectional generalisation |
| 13 | Causal interpretation | DML and association diagnostics are observational and do not replicate uniformly | All causal/mechanism language is prohibited in current claims | Unobserved confounding and measurement error remain |
| 14 | Prospective timing and deadline | Phase 8 has 20 strictly unseen sessions and returned `MIXED_EXPLORATORY`: exact replay recovered 20 contrast rows and 140 fields; three ΔB1 cells have descriptive Holm p < 0.05, while no ΔB2\|B1 cell does | The cube audit supports no aggregation change; lower dispersion is measured without causal attribution. The historical producer identity cannot be independently rehashed, and execution recovery remains outside the frozen closure. Phase 9 targets 60 complete/36 scored sessions and does not gate academic submission | Phase 8 cannot fill the PIT evidence gap or support confirmation; Phase 9 remains unread |

Decision 57's dated reference to “threat #8” identifies point-in-time availability, which
is row 7 in this matrix. The row number does not change the named threat.
