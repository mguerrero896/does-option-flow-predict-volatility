# Threats-to-validity matrix (current at 2026-08-30)

This matrix follows `data/CANONICAL_STATE.json`. Historical gate documents cannot
override it. RP2 is `NO_CURRENT_ELIGIBLE_RESULT` while
`PIT_V22_RECONCILIATION_BLOCKED` remains active. Phase 8 consumed its sole exploratory
read (`sealed_cohorts_read=1`); Phase 9 remains sealed and unread
(`sealed_cohorts_read=0`).

| # | Threat | Current evidence | Mitigation | Residual risk |
|---|---|---|---|---|
| 1 | Adaptive campaigns and multiplicity | D/V were reused for selection and recalibration; retrospective ordering was not preregistered | D/V and the consumed Phase 8 bridge are labelled exploratory; α=0.00417 is only a non-binding post-hoc sensitivity and a future-campaign budget | No retrospective correction or Phase 8 outcome can become confirmation; Phase 9 retains its separate read gate |
| 2 | Model-family dependence | Gamma, Ridge and LightGBM differ in sign and precision across D/V | Same information-set masks and session-aware model selection; family-specific reporting | No universal B1/B2 claim is supported |
| 3 | Calibration versus information | QLIKE rewards calibration; historical effects changed after recalibration and producer repairs | Retain raw/recalibrated diagnostics, but do not reconcile them into a current claim while `PIT_V22_RECONCILIATION_BLOCKED` is active | QLIKE improvement may reflect calibration repair; it cannot identify an economic mechanism |
| 4 | Multiple model/target search | Historical extensions searched many cells | Family-matched SPA/Reality Check and explicit exploratory labels | Data-dependent search remains a limit; no confirmatory discovery is claimed |
| 5 | Serial dependence and interval calibration | Five-minute origins overlap; measured bootstrap coverage was 0.784 versus nominal 0.95 in the reported check | Aggregate to sessions; block bootstrap, Newey-West and wild-cluster diagnostics | Intervals may still undercover, especially in short V |
| 6 | Target choice | Current diagnostic favors RV60 in D and RV30 in V | RV30 remains the owner-frozen primary; divergence is disclosed | Target preference is partition-dependent |
| 7 | Point-in-time availability | Source timestamps are available, but UW `created_at` and Massive SIP time do not prove historical client receipt | Claims are `PROXY_ONLY` / source-time PIT under documented assumptions; preflight fails closed | Historical client availability is not proven |
| 8 | Licensed-data reproducibility | Granular inputs cannot be redistributed | Public hashes, schemas, manifests and controlled access; Tier 2 remains separate from hermetic CI | Independent reruns require approved access and provider entitlements |
| 9 | Event/regime composition | `PITV22-C008`: stability by asset, session segment, volatility regime and latency is `NOT_EVALUATED_AFTER_PIT_CORRECTION` | Keep earlier sensitivities historical; require an authorized post-PIT stability evaluation | Regime robustness is unestablished and may not transport |
| 10 | Microstructure proxy error | RV30 is trade-price based and option-flow variables are provider-derived proxies | Noise sensitivity and source-time contracts are documented | Other proxies and feeds may yield different results |
| 11 | Common-complete selection | Information sets can drop different origins | All nested contrasts use one common mask whose digest is recorded | Results apply to common-complete origins, not every market interval |
| 12 | Narrow universe | Six liquid mega-cap equities | Scope is stated; SPY/QQQ are controls, not additional outcomes | No broad cross-sectional generalisation |
| 13 | Causal interpretation | DML and association diagnostics are observational and do not replicate uniformly | All causal/mechanism language is prohibited in current claims | Unobserved confounding and measurement error remain |
| 14 | Prospective timing and deadline | Phase 8 has only 20 strictly unseen sessions and returned `MIXED_EXPLORATORY`; Phase 9 targets 60 complete/36 scored sessions | Phase 8 publishes every aggregate outcome and its execution-recovery deviation; Phase 9 is ongoing and does not gate academic submission | Phase 8 cannot fill the PIT evidence gap or support confirmation; Phase 9 remains unread |
