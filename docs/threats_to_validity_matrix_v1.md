# Threats-to-validity matrix (current at 2026-08-28)

This matrix follows `data/CANONICAL_STATE.json`. Historical gate documents cannot
override it. No RP2 result is currently eligible; Phase 8 and Phase 9 remain sealed and
unread (`sealed_cohorts_read=0`).

| # | Threat | Current evidence | Mitigation | Residual risk |
|---|---|---|---|---|
| 1 | Adaptive campaigns and multiplicity | D/V were reused for selection and recalibration; retrospective ordering was not preregistered | D/V are labelled exploratory; α=0.00417 is only a non-binding post-hoc sensitivity and a future-campaign budget | No retrospective correction can turn D/V into confirmation; Phase 8 bridge and Phase 9 also require their separate read gates |
| 2 | Model-family dependence | Gamma, Ridge and LightGBM differ in sign and precision across D/V | Same information-set masks and session-aware model selection; family-specific reporting | No universal B1/B2 claim is supported |
| 3 | Calibration versus information | QLIKE rewards calibration; prior Gamma effects changed after recalibration and producer fixes | Calibration diagnostics and unrecalibrated/recalibrated comparisons are retained | Association cannot be assigned to an economic mechanism |
| 4 | Multiple model/target search | Historical extensions searched many cells | Family-matched SPA/Reality Check and explicit exploratory labels | Data-dependent search remains a limit; no confirmatory discovery is claimed |
| 5 | Serial dependence and interval calibration | Five-minute origins overlap; measured bootstrap coverage was 0.784 versus nominal 0.95 in the reported check | Aggregate to sessions; block bootstrap, Newey-West and wild-cluster diagnostics | Intervals may still undercover, especially in short V |
| 6 | Target choice | Current diagnostic favors RV60 in D and RV30 in V | RV30 remains the owner-frozen primary; divergence is disclosed | Target preference is partition-dependent |
| 7 | Point-in-time availability | Source timestamps are available, but UW `created_at` and Massive SIP time do not prove historical client receipt | Claims are `PROXY_ONLY` / source-time PIT under documented assumptions; preflight fails closed | Historical client availability is not proven |
| 8 | Licensed-data reproducibility | Granular inputs cannot be redistributed | Public hashes, schemas, manifests and controlled access; Tier 2 remains separate from hermetic CI | Independent reruns require approved access and provider entitlements |
| 9 | Event/regime composition | Historical sensitivity analyses changed some magnitudes but do not establish a stable effect | Report by role/family and keep event analyses historical | Regime robustness is not confirmation and may not transport |
| 10 | Microstructure proxy error | RV30 is trade-price based and option-flow variables are provider-derived proxies | Noise sensitivity and source-time contracts are documented | Other proxies and feeds may yield different results |
| 11 | Common-complete selection | Information sets can drop different origins | All nested contrasts use one common mask whose digest is recorded | Results apply to common-complete origins, not every market interval |
| 12 | Narrow universe | Six liquid mega-cap equities | Scope is stated; SPY/QQQ are controls, not additional outcomes | No broad cross-sectional generalisation |
| 13 | Causal interpretation | DML and association diagnostics are observational and do not replicate uniformly | All causal/mechanism language is prohibited in current claims | Unobserved confounding and measurement error remain |
| 14 | Prospective timing and deadline | Phase 8 has only 20 strictly unseen sessions; Phase 9 targets 60 complete/36 scored sessions | Phase 8 is an exploratory bridge; Phase 9 is ongoing and does not gate academic submission | Neither unopened cohort can be used to fill the current evidence gap before its authorized one-shot read |
