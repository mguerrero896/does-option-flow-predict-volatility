# Seasonal persistence and HAR-RV references

Robustness committed in the proposal, executed after the primary read; does not select models or change the headline; reported regardless of outcome.

These are nominal post-primary comparisons. Lower QLIKE is better; a positive delta favors the existing model over the reference. Percentile intervals are 95%, using five-session blocks, 9,999 resamples and seed 20260907; the centered one-sided nominal p-value uses the +1 correction. No headline or registered sequence changes.

| RV | Reference | QLIKE | 95% CI | Origins | Excluded | Sessions |
|---:|---|---:|---|---:|---:|---:|
| 15 | seasonal_persistence | 0.55791697 | [0.51392765, 0.60579439] | 159054 | 1778 | 417 |
| 15 | HAR_dwm | 0.40806067 | [0.3650684, 0.4774715] | 160832 | 0 | 419 |
| 30 | seasonal_persistence | 0.40648313 | [0.36953656, 0.44629919] | 158959 | 1873 | 417 |
| 30 | HAR_dwm | 0.3396231 | [0.30128494, 0.39945975] | 160832 | 0 | 419 |

HAR is an intraday OLS adaptation in levels with an intercept, asset effects and daily/weekly/monthly components; it is neither HARQ nor the primary linear model. The monthly component uses 22 previous daily observations from B0; the daily component already contains a lag and is not shifted again. The rule retains 22 complete records without skipping nulls.

Among 2,514 evaluation asset-session records, 252 monthly windows have XNYS gaps between record dates. The panel does not retain the effective date of each underlying daily RV. The monthly component therefore represents 22 previous available observations, not necessarily 22 consecutive XNYS sessions.

Seasonal persistence requires the immediately preceding XNYS session and h+1 observed closes; it does not skip to another session or fill missing stretches. Reference and model losses share the same intersection. The original B1/B0 and B2/B1 comparisons were also recalculated on that intersection.

| RV | Reference | Family | Set | Model QLIKE | Delta | 95% CI | p nominal |
|---:|---|---|---|---:|---:|---|---:|
| 15 | seasonal_persistence | log_ridge_harq | B0 | 0.18205418 | 0.37586279 | [0.33818818, 0.41595613] | 0.0001 |
| 15 | seasonal_persistence | log_ridge_harq | B1 | 0.18059112 | 0.37732585 | [0.33941206, 0.41776925] | 0.0001 |
| 15 | seasonal_persistence | log_ridge_harq | B2 | 0.17947073 | 0.37844624 | [0.34055154, 0.41866073] | 0.0001 |
| 15 | seasonal_persistence | lightgbm_qlike | B0 | 0.18434855 | 0.37356842 | [0.33611424, 0.41336048] | 0.0001 |
| 15 | seasonal_persistence | lightgbm_qlike | B1 | 0.18246724 | 0.37544973 | [0.33784472, 0.41546314] | 0.0001 |
| 15 | seasonal_persistence | lightgbm_qlike | B2 | 0.18188888 | 0.37602809 | [0.33814885, 0.41618503] | 0.0001 |
| 15 | HAR_dwm | log_ridge_harq | B0 | 0.18366037 | 0.2244003 | [0.1864176, 0.28347618] | 0.0001 |
| 15 | HAR_dwm | log_ridge_harq | B1 | 0.18204406 | 0.22601661 | [0.1875044, 0.2861878] | 0.0001 |
| 15 | HAR_dwm | log_ridge_harq | B2 | 0.1809103 | 0.22715037 | [0.18854206, 0.28724404] | 0.0001 |
| 15 | HAR_dwm | lightgbm_qlike | B0 | 0.18775026 | 0.22031041 | [0.18518057, 0.27406298] | 0.0001 |
| 15 | HAR_dwm | lightgbm_qlike | B1 | 0.18555364 | 0.22250703 | [0.1869063, 0.27765132] | 0.0001 |
| 15 | HAR_dwm | lightgbm_qlike | B2 | 0.18576654 | 0.22229413 | [0.1872349, 0.27584181] | 0.0001 |
| 30 | seasonal_persistence | log_ridge_harq | B0 | 0.14632142 | 0.26016171 | [0.23042979, 0.29219781] | 0.0001 |
| 30 | seasonal_persistence | log_ridge_harq | B1 | 0.14390009 | 0.26258303 | [0.23256643, 0.29502693] | 0.0001 |
| 30 | seasonal_persistence | log_ridge_harq | B2 | 0.14309347 | 0.26338966 | [0.23325154, 0.29567704] | 0.0001 |
| 30 | seasonal_persistence | lightgbm_qlike | B0 | 0.14677497 | 0.25970816 | [0.22975162, 0.29165992] | 0.0001 |
| 30 | seasonal_persistence | lightgbm_qlike | B1 | 0.14388734 | 0.26259579 | [0.23278675, 0.29451878] | 0.0001 |
| 30 | seasonal_persistence | lightgbm_qlike | B2 | 0.14352223 | 0.2629609 | [0.23317613, 0.29479079] | 0.0001 |
| 30 | HAR_dwm | log_ridge_harq | B0 | 0.14730674 | 0.19231636 | [0.16014066, 0.24061219] | 0.0001 |
| 30 | HAR_dwm | log_ridge_harq | B1 | 0.14475984 | 0.19486325 | [0.1619131, 0.24479176] | 0.0001 |
| 30 | HAR_dwm | log_ridge_harq | B2 | 0.14395746 | 0.19566564 | [0.16288324, 0.24543789] | 0.0001 |
| 30 | HAR_dwm | lightgbm_qlike | B0 | 0.14931695 | 0.19030614 | [0.16004291, 0.2347679] | 0.0001 |
| 30 | HAR_dwm | lightgbm_qlike | B1 | 0.14619447 | 0.19342863 | [0.16281526, 0.23910839] | 0.0001 |
| 30 | HAR_dwm | lightgbm_qlike | B2 | 0.14642711 | 0.19319598 | [0.16302861, 0.23765489] | 0.0001 |

All 24 contrasts favor the existing models within these comparable samples. This does not establish universality, causality, historical client receipt or profitability, and does not correct prior cross-version search. The seasonal sample excludes 1,778 origins at RV15 and 1,873 at RV30; both cover 417 sessions. HAR covers 419 sessions with no exclusions.

[QLIKE](reference_qlike.csv), [contrasts](reference_contrasts.csv), [matched observed contrasts](reference_matched_observed_contrasts.csv), [diagnostic census](reference_diagnostics_receipt.json), [source execution receipt](references_receipt.json) and [import provenance](import_receipt.json). Detailed forecasts and licensed inputs are not redistributed.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
