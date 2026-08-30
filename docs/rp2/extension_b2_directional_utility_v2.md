# B2 directional utility: the lead is not strong enough to pursue

Status: `EXPLORATORY_DIRECTIONAL_REANALYSIS`
Decision: `DO_NOT_PURSUE`
Capital status: `RESEARCH_ONLY`, `NOT INVESTMENT ADVICE`, `capital_go=false`

## Finding

Do not start another research program from this three-feature directional lead. The
registered test did not pass its decision rule. The validation estimates remain positive,
and the 120-minute nominal interval excludes zero, but neither 60 nor 120 minutes survives
the 68-test Holm family. Both effects are also smaller than their familywise minimum
detectable effects (MDEs). The strict sign falsifier did not fire, so this is failure to
establish a useful directional mechanism, not proof that the population effect is zero.

Source: `artifacts/rp2_ext1_directional_v2/results.json#/directional/decision` and
`#/directional/tests/dml~1V_all~1matched120_tod~1h60|h120`.

## Why the design changes before the result changes

The frozen Ext1 battery asks whether a ten-feature B2 block contains information about 36
alternative targets. It does not estimate a usable directional score. Its horizon samples
also differ because an origin must leave enough trading minutes for its target. A stronger
120-minute test can therefore reflect morning-only sampling rather than horizon.

The reanalysis separates those questions:

1. A fixed score turns the three same-sign features into one directional instrument.
2. Native-horizon samples preserve the original estimand.
3. A 120-minute matched sample gives every horizon identical rows.
4. Adding and removing `minutes_since_open` and `minutes_to_close` isolates explicit
   time-of-day partialization from row matching.
5. One global Holm family covers every reported primary p-value.

The contract was frozen before result execution at
`configs/rp2_ext1_directional_v2.json`, SHA-256
`fc083b0d9df26e913f4348d9c64f4cd8e83b8e963169743d0d5cd6dd5488ebde`. It defines 60
DML effects (3 modes x 4 cells x 5 horizons) and 8 balanced-sign-accuracy tests, for a
family of 68. Every p-value is two-sided; Holm controls familywise error at 0.05. MDEs use
alpha `0.05 / 68`, 80% power, and the registered long-run-variance producer.

The pursue rule required both validation matched-sample effects at 60 and 120 minutes to
have positive theta, a positive nominal 95% lower bound, Holm p <= 0.05, and magnitude at
least the familywise MDE. Native-sample effects also had to keep the positive sign. The
operational falsifier is failure of any condition. The stronger directional falsifier is a
nonpositive upper interval bound at validation 120 minutes.

Source: `configs/rp2_ext1_directional_v2.json#/family` and `#/decision_rule`.

## The frozen artifact cannot be reproduced exactly

The frozen file is intact: SHA-256
`604e1e40990b1a9a6e0800691f0cb1dca0db658781f23838b8f49d47f263f499`. Exact
reproduction cannot be confirmed because it records no panel hashes, bar hashes, session
identity, feature-registry digest, or code commit. Its B2 treatment list also contains
`b2_5m_hawkes_innovation`; the corrected registry contains
`b2_5m_decay_intensity_innovation`.

The closest auditable comparison runs the corrected estimator on the three named bar
sources in the frozen campaign. Even that route has 240 discovery clusters rather than the
frozen 230, so it is a same-source comparison, not a claim of equal inputs. The exact-width
factorial supersedes the earlier discovery entries `45.721` and `39.153`: those entries
silently tested 12 columns (10 named treatments plus two missingness indicators) while
serializing only 10 coefficient names. The validation design had no treatment missingness
indicators, so its Wald values are unchanged; its Holm values change because this battery
has 40 tests rather than 68.

| Role / target | Frozen rows / sessions | Frozen Wald / Holm p | Exact-10 August rows / sessions | Wald / df / raw p / 40-test Holm p |
|---|---:|---:|---:|---:|
| D signed return 60m | 81,790 / 230 | 28.896 / 0.01554 | 84,972 / 240 | 15.138 / 10 / 0.12710 / 1.00000 |
| D signed return 120m | 65,653 / 230 | 25.878 / 0.03908 | 67,812 / 240 | 14.079 / 10 / 0.16940 / 1.00000 |
| V signed return 60m | 28,328 / 80 | 34.253 / 0.005855 | 28,680 / 80 | 24.581 / 10 / 0.006200 / 0.21079 |
| V signed return 120m | 22,784 / 80 | 46.317 / 0.0000452 | 22,944 / 80 | 28.608 / 10 / 0.001442 / 0.05479 |

No validation target survives Holm in the corrected same-source battery. The frozen
directional conclusion therefore changes under the current corrected inputs and estimator.
The comparison does not identify one causal repair because several frozen input identities
are unavailable.

One premise also fails against the frozen file itself: validation `y_rs_up_60`, a positive
semivariance target, survives its 36-test Holm family at `0.03576`. The frozen validation
survivors are `y_rs_up_60`, `y_signed_return_60`, and `y_signed_return_120`, not two
directional targets alone.

Source for the exact-width table:
`artifacts/rp2_ext1_directional_factorial_v1/results.json#/tests`. Frozen source:
`artifacts/rp2_ext1_mechanism_utility/mechanism_utility.json#/D|V/a_other_targets`.

## Coverage and repaired guards

The target producer now rejects nonfinite prices before `log_returns`, records every guard,
and uses the exchange-calendar session length already implemented in `rp2.bars`. It accepts
210-minute early closes rather than inventing 180 flat minutes. A second blocker surfaced
after the NaN fix: the ranking path did not pass sessions to the current boosted-model
route and stopped at `RP2_LADDER_BOOSTED_SESSIONS_REQUIRED`. The producer now uses the
registered session-aware ladder entry point.

| Coverage fact | Three-source comparison | Current five-source run |
|---|---:|---:|
| Bar asset-sessions seen | 2,280 | 3,752 |
| Panel asset-sessions with bars | 1,920 | 2,814 |
| Accepted asset-sessions | 1,908 | 2,802 |
| Requested asset-sessions without a bar group | 894 | 0 |
| Rejected: fill share > 5% | 0 | 0 |
| Rejected: nonfinite close | 12 | 12 |
| Rejected: nonpositive close | 0 | 0 |
| True early-close asset-sessions | 24 | 30 |
| Target rows emitted | 125,100 | 183,888 |

The five-source route adds 894 accepted asset-sessions and 58,788 target rows. The 938 bar
asset-sessions without panel origins are SPY/QQQ market-control groups, not silent target
loss. The recorded count of 40 high-fill sessions does not reproduce on the current stores:
the measured count is zero. The 12 leading-price gaps remain explicit exclusions and remove
744 panel origins from the target frame.

Source: `artifacts/rp2_ext1_directional_v2/results.json#/coverage`.

## Treatment x coverage factorial

The frozen contract names these exact 10 `CORE_TREATMENTS`:
`vega_flow`, `gamma_flow`, `delta_flow`, `premium`, `trades`,
`hawkes_innovation`, `d_iv`, `buy_premium_share`, `strike_hhi`, and
`otm_premium_share`, each with the `b2_5m_` prefix. The comparison set is the exact current
12-feature `B2_CORE` registry: `buy_premium_share`, `d_iv`,
`decay_intensity_innovation`, `delta_flow`, `mean_provider_latency_s`,
`multileg_size_share`, `premium`, `strike_hhi`, `trades`, `vega_flow`,
`vega_flow_short_dte`, and `zero_dte_premium_share`, also with that prefix.

The four requested cells use the same cross-fitted partial-out DML joint Wald, session
clustering, five folds, one-session purge, and B0+B1 nuisance block. The family is the 40
two-sided joint tests formed by 2 treatment sets x 2 coverages x 2 roles x 5 horizons, with
one global Holm adjustment. Each table entry is `Wald / df / raw p / Holm p`.

| Treatment set / coverage | D 60m | D 120m | V 60m | V 120m |
|---|---:|---:|---:|---:|
| Exact Ext1 / August | 15.138 / 10 / 0.12710 / 1.00000 | 14.079 / 10 / 0.16940 / 1.00000 | 24.581 / 10 / 0.006200 / 0.21079 | 28.608 / 10 / 0.001442 / 0.05479 |
| Exact Ext1 / complete | 16.673 / 10 / 0.081921 / 1.00000 | 21.702 / 10 / 0.016694 / 0.43405 | 24.581 / 10 / 0.006200 / 0.21079 | 28.608 / 10 / 0.001442 / 0.05479 |
| B2 panel 12 / August | 31.326 / 12 / 0.001757 / 0.063246 | 24.797 / 12 / 0.015812 / 0.42693 | 27.287 / 12 / 0.007024 / 0.22477 | 26.729 / 12 / 0.008451 / 0.24507 |
| B2 panel 12 / complete | 35.129 / 12 / 0.0004467 / 0.017421 | 41.035 / 12 / 0.00004835 / 0.001934 | 27.287 / 12 / 0.007024 / 0.22477 | 26.729 / 12 / 0.008451 / 0.24507 |

The preregistered descriptive scale is `log(Wald / df)`. Across D/V and the 60/120-minute
targets, the median absolute treatment-set shift is `0.33471`; the coverage shift is
`0.052785`, a ratio of `6.34`. The registered classification is therefore
`TREATMENT_SET`, not `COVERAGE`. This is not universal across contrasts: at D 120 minutes
the coverage main effect (`0.46820`) is slightly larger than the treatment main effect
(`0.41919`). The sets are not nested, so the classification is descriptive, not causal.
Only B2-panel-12 with complete coverage at D 60 and D 120 survives the global 40-test Holm
family.

That result does **not** explain the historical validation decline. Complete coverage adds
894 accepted asset-sessions and 58,788 target rows to D, but zero rows to every V horizon;
the August and complete V statistics are therefore identical. Holding the exact Ext1 set
and August sources still gives V Wald `24.581` and `28.608`, below the frozen `34.253` and
`46.317`. Switching to B2 panel 12 gives `27.287` and `26.729`, so it does not restore the
120-minute statistic. For the frozen-to-current validation decline, the answer is
`NEITHER_TREATMENT_SET_NOR_COVERAGE`; the unresolved remainder lies in corrected inputs,
estimator/preprocessing, or session identity that the frozen artifact did not hash.

The obsolete `b2_5m_hawkes_innovation` label was resolved as a
`RECORDED_SEMANTIC_RENAME` to `b2_5m_decay_intensity_innovation`, as documented in
`docs/rp2/block7_dml_v1.md`: the feature was built with fixed baseline/excitation/decay
inputs and is a decay-intensity innovation, not an estimated Hawkes process. The producer
maps the historical label to the current panel column in memory, retains the historical
coefficient label, applies the registered signed transform, and does not recompute values.
The old column is absent, so historical byte equality cannot be tested.

The exact-width run also exposed the missingness-indicator defect described above. The
producer now omits treatment missingness indicators so the blocks remain exactly 10 and
12 columns, while retaining fold-local imputation and scaling. The shared DML function now
fails closed with `RP2_DML_TREATMENT_NAME_WIDTH` if names and matrix width diverge.

Contract: `configs/rp2_ext1_directional_factorial_v1.json`, semantic SHA-256
`290debdca033737e386c5abe9cca4e0b1d7632435e07f747823198864da256a4`. Result:
`artifacts/rp2_ext1_directional_factorial_v1/results.json`, semantic self-hash
`34cd6d52722692c03207625011d15160d5a4e27bb08676aad191e63ffc054913`, file SHA-256
`9c93ad6a16471cc52034edf55d3a3c127117db5dbe06f226e75de98ceda50825`.

## Horizon and time of day

Theta is signed log return per one unit of the fixed normalized score. The table expresses
theta, standard error, interval, and MDE in basis points (`log return x 10,000`). Holm p is
global across all 68 tests.

| V mode / horizon | Rows | Theta (bp) | SE (bp) | Nominal 95% CI (bp) | Raw p | Holm p | MDE (bp) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Native + time controls, 60m | 28,680 | 1.829 | 0.825 | [0.186, 3.472] | 0.0296 | 1.000 | 3.599 |
| Native + time controls, 120m | 22,944 | 3.034 | 1.405 | [0.238, 5.831] | 0.0338 | 1.000 | 6.125 |
| Matched, no time controls, 60m | 22,944 | 1.645 | 0.998 | [-0.341, 3.631] | 0.1031 | 1.000 | 4.349 |
| Matched, no time controls, 120m | 22,944 | 3.066 | 1.398 | [0.284, 5.848] | 0.0312 | 1.000 | 6.093 |
| Matched + time controls, 60m | 22,944 | 1.645 | 0.998 | [-0.341, 3.632] | 0.1032 | 1.000 | 4.351 |
| Matched + time controls, 120m | 22,944 | 3.034 | 1.405 | [0.238, 5.831] | 0.0338 | 1.000 | 6.125 |

Matching reduces the 60-minute estimate by about 10% and removes its nominal rejection.
The 120-minute sample is already the matched sample. Explicit time controls move the
60-minute theta by less than `0.001` bp and the 120-minute theta by `0.032` bp. The increase
with horizon therefore remains on identical rows and is not explained by these two
time-of-day controls. It still does not establish utility: all six Holm p-values are 1.0,
and every magnitude is below its MDE.

Source: `artifacts/rp2_ext1_directional_v2/results.json#/directional/tests/` with keys
`dml/V_all/native_tod/*`, `dml/V_all/matched120_no_tod/*`, and
`dml/V_all/matched120_tod/*`.

## Directional instrument

The score is

`(z(strike_hhi) - z(log(premium)) - z(buy_premium_share)) / sqrt(3)`.

Registry transforms, medians, means, and scales are fitted on all D rows without outcomes
and then frozen for every cell. Positive score predicts positive return. The signs come
from the frozen exploratory finding, so this remains a selected, exploratory instrument.

| V matched metric | 60m | 120m |
|---|---:|---:|
| Session-balanced accuracy | 50.589% | 51.006% |
| Sign hit rate | 50.333% | 50.705% |
| Nominal 95% CI for balanced accuracy | [49.410%, 51.769%] | [49.508%, 52.505%] |
| Raw p / Holm p | 0.323 / 1.000 | 0.185 / 1.000 |
| Wild-cluster p / Newey-West p | 0.330 / 0.254 | 0.177 / 0.185 |
| Familywise MDE above 50% | 2.583 pp | 3.282 pp |

The instrument does not beat chance under any registered inference route. It does not
measure a causal effect, probability calibration, trading profit, implementability,
transaction costs, slippage, capacity, or risk-adjusted return.

Source: `artifacts/rp2_ext1_directional_v2/results.json#/instrument` and
`#/directional/tests/metric~1V_all~1matched120_tod~1h60|h120`.

## Era evidence and the withdrawn volatility-decay line

The primary matched-and-time-controlled effects do not show a statistically resolved era
path. D is split at its fixed midpoint: 194 sessions through 2025-06-11 and 195 sessions
from 2025-06-12 through 2026-03-23. V contains 80 sessions from 2026-03-24 through
2026-07-17.

| Cell | Horizon | Theta (bp) | Nominal 95% CI (bp) | Raw p | Holm p | MDE (bp) |
|---|---:|---:|---:|---:|---:|---:|
| D early | 60m | 0.183 | [-1.084, 1.451] | 0.776 | 1.000 | 2.747 |
| D early | 120m | 0.010 | [-1.807, 1.827] | 0.991 | 1.000 | 3.938 |
| D late | 60m | 0.552 | [-0.360, 1.464] | 0.234 | 1.000 | 1.976 |
| D late | 120m | 0.739 | [-0.549, 2.028] | 0.259 | 1.000 | 2.793 |
| V | 60m | 1.645 | [-0.341, 3.632] | 0.103 | 1.000 | 4.351 |
| V | 120m | 3.034 | [0.238, 5.831] | 0.0338 | 1.000 | 6.125 |

Point estimates rise rather than decay, but every era estimate is below its familywise MDE
and every Holm p is 1.0. A monotone trend is not measured and must not be inferred from the
table.

The `-0.0277/year` volatility-decay line is marked `WITHDRAWN_INVALIDATED` in
`docs/rp2_v3/SUPERSEDED_RESULTS.md`. It is not a current benchmark, and its estimand is not
the signed-return score theta. No valid numerical comparison to `-0.028/year` can be made.

Source for era estimates:
`artifacts/rp2_ext1_directional_v2/results.json#/directional/tests/dml~1D_early|D_late|V_all~1matched120_tod`.
Source for comparator status: `docs/rp2_v3/SUPERSEDED_RESULTS.md`, withdrawal row dated
2026-08-28, and `results.json#/historical_decay_comparator`.

## What is not measured

- Exact frozen-input reproduction is not measured because the frozen artifact lacks the
  required identities. Exact reproduction cannot be confirmed.
- A formal era slope is not measured; the registered era cells are reported without a
  post-hoc trend test.
- Out-of-sample confirmation is not measured. D and V are already-read research roles.
- Phase 8, Phase 9, and cohort C were not read, moved, regenerated, or counted.
- RP3 remains sealed and unchanged. This result does not alter its fixed sequence or spend
  a look.
- No capital, order, email, deployment, or canonical-outcome action occurred.

## Provenance and verification

The aggregate result has semantic self-hash
`477f21af6319de58bee2eeeca930c9cccbd497371086a0f7117ab92123e656b0` and file SHA-256
`d4e7f0978ad7942e442ebe2ab0bdd65ba3f46908a52eb72058dd16d133077b12`. It records code
commit `b93ee32e5f149038cd042fe706c5b0a94f5e2f08`, all three panel hashes, all five bar-source
hashes, `inference_config_digest`, 68 test records, and `sealed_cohorts_read=0`.

The factorial result has semantic self-hash
`34cd6d52722692c03207625011d15160d5a4e27bb08676aad191e63ffc054913` and file SHA-256
`9c93ad6a16471cc52034edf55d3a3c127117db5dbe06f226e75de98ceda50825`. It records code
commit `8758d4686bef2403a8f716eb79a5d9a2be60c985`, the same input identities, 40 test records,
both mask invariants, exact requested/resolved treatment names, and `sealed_cohorts_read=0`.

Final verification commands:

```powershell
uv run ruff check .
uv run mypy
$env:MDS650_PANEL_GUARD_MAY_SKIP='1'; uv run pytest -q
git status --short
```

The verification table is updated only from the final command outputs after this document
and its contract test are present:

| Check | Result |
|---|---|
| Ruff | PASS: `All checks passed!` |
| Mypy strict | PASS: no issues in 324 source files |
| Full pytest suite | PASS: 100%, exit 0; three contract skips |
| Frozen artifact SHA-256 | PASS: `604e1e4099...f263f499` |
| New semantic self-hash | PASS: `477f21af63...3e656b0` |
| Factorial semantic self-hash | PASS: `34cd6d5272...c054913` |
| Licensed parquet or CSV in Git status | PASS: none tracked or untracked |

Artifact sources for the numerical claims:
`artifacts/rp2_ext1_directional_v2/results.json` (`schema_version`
`rp2-ext1-directional-v2-results-v1.0`) and
`artifacts/rp2_ext1_directional_factorial_v1/results.json` (`schema_version`
`rp2-ext1-directional-factorial-results-v1.0`).
