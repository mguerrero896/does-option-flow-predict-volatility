# Options Order Flow and Intraday Volatility

**Does options order flow improve forecasts beyond price history and the implied volatility surface?**

[![Tier 1 CI](https://github.com/mguerrero896/does-option-flow-predict-volatility/actions/workflows/ci.yml/badge.svg)](https://github.com/mguerrero896/does-option-flow-predict-volatility/actions/workflows/ci.yml)

Earlier tests set a demanding context: RP2's validation comparisons were null or
negative across the tested model families and its economic tests found no usable value;
the point-in-time successor concluded `GLOBAL_EDGE_NOT_CONFIRMED`; Phase 8 returned
`MIXED_EXPLORATORY`. Their corrections remain in the
[scientific findings ledger](docs/scientific_findings_ledger.md).

RP4 v4 finds a **small, conditional forecasting improvement**. Option state improves
mean RV30 and RV15 forecasts in both families under the v3/v4 rules. Linear flow at
15 minutes adds **+0.623 % QLIKE reduction**, with a **positive 95% interval** for the
QLIKE difference [0.000335; 0.001932], one-sided **p = 0.0032**, and bilateral
Holm-adjusted **p = 0.0248** in a separate comparability analysis. Its sign is positive
in **six of six assets**. In trees, flow does not pass the mean test. This is neither
a universal advantage nor evidence of profitability.
[Saved statistics](artifacts/rp4_v4_b4/primary_statistics.csv) ·
[Stability checks](artifacts/rp4_v4_b4/robustness.csv) ·
[Canonical defense](docs/rp4/DEFENSE_PACKAGE/revision_2/correction_7/README.md).

**Limits:** 419 evaluated historical sessions; fourth evaluation of reused windows;
no full-sequence confirmation in the final 25-session window; prospective replication
pending. Walk-forward training preserves chronology within each fit, while the design
was fixed on 2026-09-07 after the historical sample had been observed.
[Registered design](docs/rp4/specification_v4.md).

## Question, hypotheses and data

The original proposal asked whether options activity adds information about future
intraday realized variance beyond a competitive price-history baseline. Its mechanism
was that trading activity and position-sensitive option state might contain different
information. RP4 makes that distinction explicit with nested sets: **B0** price and
volatility history, **B1** B0 plus the implied volatility surface and option state,
**B2** B1 plus options order flow, composition and signed imbalance. The v3/v4 sets
have **29/69/138 predictors**, before family-specific indicators and asset effects.
[Proposal alignment and deviations](docs/rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md).

Six outcomes: AAPL, AMZN, META, MSFT, NVDA and TSLA. Licensed one-minute bars and
options trades supply point-in-time data under a **120-second source-time proxy**;
historical receipt by a trading client is unproven. Sources are FMP, Unusual Whales
and Massive. The UW gap **2025-01-25–2025-02-24** is retained without filling.
[Data access](data/DATA_ACCESS.md) · [PIT limits](docs/pit_v22_claims_and_limitations.md).

H1 tests whether B1 reduces mean QLIKE relative to B0; H2 tests B2 relative to B1.
QLIKE measures forecast loss, not trading profit. Expanding walk-forward evaluation
uses **60 warm-up sessions**, the last **10 training sessions** for selection,
**60-minute purge/embargo**, and a calendar partition at **2026-08-01**. Inference
uses **9,999** circular bootstrap resamples of **five-session blocks**. The linear
family is winsorized with rank filtering (nominal ridge); the other is LightGBM.
[Full v4 report](docs/rp4/results_v4.md).

The move from RV30 to **15-minute primary / 5-minute secondary** targets was a
disclosed, conditionally predeclared design improvement, alongside coverage and
numerical repairs. It changes the estimand and supplies neither independent
replication nor evidence of an optimal horizon.
[Decisions and deviations](docs/research_decisions_current.md).

## Results: size, sign and limits

Cells show **percentage QLIKE reduction (p)**. Negative values mean worse forecasts.
v1/v2 use bilateral Holm-adjusted p-values; v3/v4 use one-sided H1→H2 at 5% per family.
H2 opens only when H1 rejects. Cross-version search is not adjusted. V4 remains the headline;
the closed registered exploratory v5 extension is reported separately.

| Version / target | Linear B1/B0 | Linear B2/B1 | Trees B1/B0 | Trees B2/B1 | Sessions |
| --- | ---: | ---: | ---: | ---: | ---: |
| v1 · RV30 | +0.290 % (1.0000) | −167,448.32 % (1.0000) | +1.204 % (0.4724) | −0.073 % (1.0000) | 418 |
| v2 · RV30 | +1.715 % (0.1842) | −8.714 % (0.3752) | +2.091 % (0.0264) | −0.063 % (0.8858) | 419 |
| v3 · RV30 | +1.729 % (0.0439) | +0.554 % (0.0525) | +2.091 % (0.0053) | −0.159 % (0.6631) | 419 |
| v4 · RV15, primary | +0.880 % (0.0390) | +0.623 % (0.0032) | +1.170 % (0.0135) | −0.115 % (0.6280) | 419 |
| v4 · RV5, secondary | +0.377 % (0.0092) | +0.256 % (0.0172) | +0.536 % (0.0608) | +0.160 % (not opened; nominal 0.1927) | 419 |

[All 40 comparison cells and source hashes](artifacts/rp4_closeout_figures/comparison_v1_v4.csv).
v1's numerical failure is retained. Coverage and specification changed between
versions; their differences do not isolate one repair's causal effect.

The [closed registered exploratory v5 extension](docs/rp4/results_v5.md) compares
five RV15 families. Its primary selector fails H1 (p = 0.3594), so its H2 is not
opened. The secondary top2 ensemble passes both tests; Holm across the two selector
chains gives p = 0.0498. The declared Bonferroni ×5 bound across historical versions
is 0.249 and does not pass; it does not correct all adaptive search.
The disclosed post hoc averaging analysis also reuses these historical sessions.
It motivates secondary prospective comparisons and supplies no new confirmation.

The [eight-asset extension (registered, closed)](docs/rp4/results_universe_v1.md)
adds SPY/QQQ as targets: linear option state and flow improve QLIKE by **1.40%**
(p = 0.0208) and **0.56%** (p = 0.0093). Trees fail H1; the joint claim across both
families fails. It reuses the historical period and preserves the v4 headline.

![RP4 forecast-loss comparisons and uncertainty](docs/figures/rp4/thesis_summary.svg)

The final 25-session window does not confirm the full sequence. RV5 is secondary:
linear flow improves **+0.256 %**, with positive signs in **three of six assets**.
Positive tree medians are secondary and do not replace the primary mean test.
The dealer-hedging mechanism, economic alpha and broader generalization remain unproven.
[Findings](docs/scientific_findings_ledger.md) ·
[Defects and resolutions](docs/known_defects_and_resolutions.md) ·
[Validity](docs/threats_to_validity_matrix_v1.md).

## Reproduce

From a clean clone, install Python 3.12 and `uv`, then install the locked environment:

```sh
uv sync --frozen
uv run --frozen pytest tests/contract tests/test_gated_history_contract.py -q
uv run --frozen python scripts/sync_supabase_catalog.py --rp4-v4 --dry-run
```

Public aggregate CSVs support numerical cross-checks, figure regeneration and
artifact-hash verification. Rebuilding feature panels or refitting the study requires
licensed inputs and their recorded hashes. Exact checked commands and boundaries:
[reproduction guide](docs/reproduce.md) ·
[reproducibility contract](docs/reproducibility_contract_v1.md) ·
[numbered reading route](docs/INDEX.md). A public check is not a new scientific evaluation.

## History and prospective replication

RP2's weak validation evidence, infeasible power plans and lack of economic value
are compatible with a small, family-specific v4 forecast-loss reduction: they concern
different effects and uncertainty. **335 sessions** is a normal-approximation power
plan for v4 H2, not guaranteed success or 80% joint H1/H2 power. The earlier
**537-session** RP2 plan concerned its own effect.
[Reconciliation and sources](docs/scientific_findings_ledger.md).

RP4 distinguishes **20 new sessions**, a **40-session** stability check, a secondary
**45-session combination of 25 historical + 20 new**, and a final **335-session**
extension. RP3 retains its registered gate, with **2029-01-30** as the estimated date,
not a completed read. Phase 8's historical bridge was consumed; its audit found
**no aggregation change** and was **not confirmatory**. Its sensitivity improved
**one of eight B1-inclusive primary cells**.
[Phase 8 record](reports/phase8a_exploratory_bridge_addendum_v13.md) ·
[RP3 preregistration](docs/rp3/PREREGISTRATION.md).

<details>
<summary>Historical bundle identity retained for audit</summary>

`rp2-v3-20260831-b1-spot-cutoff-remediation` retains scientific hash
`033f2eb6be35e5db06aec2f9e01ef5f3379a8be68b0372087f24e40fa681bea4` and disposition
`HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM`, for
`SUPERSEDED_BY_PIT_V22_SUCCESSOR_V2`. These are historical identifiers.
[Superseded measurements](docs/rp2_v3/SUPERSEDED_RESULTS.md) ·
[Machine-readable state](data/CANONICAL_STATE.json) · [Generated state](STATUS.md).

</details>

## Navigation

[Contributing](CONTRIBUTING.md) · [Documentation](docs/INDEX.md) ·
[Development guide](docs/DEVELOPER_GUIDE.md) ·
[Computational assistance](docs/AI_ASSISTANCE_STATEMENT.md) ·
[Validity](docs/threats_to_validity_matrix_v1.md) · [Scripts](scripts/README.md) ·
[Reports](reports/INDEX.md) · [Database](supabase/README.md) ·
[Issues](https://github.com/mguerrero896/does-option-flow-predict-volatility/issues) ·
[Citation](CITATION.cff) · [License](LICENSE) · [Security](SECURITY.md).

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
