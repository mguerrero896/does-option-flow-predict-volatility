Out-of-sample walk-forward evaluation; partition fixed on 2026-09-07.

# Do options improve intraday volatility forecasts?

Yes for option-state information; for flow, the answer depends on the horizon, family and statistic. The RP4 closeout rule was met at RV15 in the linear family. The scientific programme ends at v4, without a v5.

## Question and test

Realised variation is forecast for AAPL, AMZN, META, MSFT, NVDA and TSLA using one-minute bars and options trades. The three sets are nested: B0 uses prices and volatility history; B1 adds option-state and options-surface information; B2 adds flow composition, activity and signed imbalance. In v3/v4 they have 29, 69 and 138 predictors, respectively, plus the asset effects and presence indicators appropriate to each family.

Development spans 2024-08-02–2026-07-31. The calendar split is 2026-08-01, fixed on 2026-09-07. Each session is predicted using exclusively earlier expanding training data, after 60 warm-up sessions, with selection on the last ten training sessions and a purge/embargo of 60 minutes. The v2–v4 primary window has 419 sessions and 160,832 origins; the window termed confirmation, 2026-08-03–2026-09-04, has 25 sessions and 9,750 origins.

A linear family and LightGBM are compared. In v3/v4 the linear family is a **winsorised linear model with a rank filter (nominal ridge)**. QLIKE loss measures forecast error, not profitability. In v3/v4, H1 tests B1 over B0 at one-sided 5%; only if it rejects is H2, B2 over B1, tested, also at 5%. The closeout rule requires the sequence in at least one family, not both. The bootstrap uses five-session blocks; the p-values do not correct the search across versions.

## Primary result for each version

Each cell shows **percentage reduction in QLIKE (p)**. A negative sign means deterioration. In v1/v2, p is two-sided with Holm adjustment; in v3/v4 it is sequential and one-sided. The p-values from different versions are therefore not interchangeable.

| Version / target | Linear B1/B0 | Linear B2/B1 | Trees B1/B0 | Trees B2/B1 | Sessions |
| --- | ---: | ---: | ---: | ---: | ---: |
| v1 · RV30 | +0.290 % (1.0000) | −167,448.32 % (1.0000) | +1.204 % (0.4724) | −0.073 % (1.0000) | 418 |
| v2 · RV30 | +1.715 % (0.1842) | −8.714 % (0.3752) | +2.091 % (0.0264) | −0.063 % (0.8858) | 419 |
| v3 · RV30 | +1.729 % (0.0439) | +0.554 % (0.0525) | +2.091 % (0.0053) | −0.159 % (0.6631) | 419 |
| v4 · RV15, primary | +0.880 % (0.0390) | +0.623 % (0.0032) | +1.170 % (0.0135) | −0.115 % (0.6280) | 419 |
| v4 · RV5, secondary | +0.377 % (0.0092) | +0.256 % (0.0172) | +0.536 % (0.0608) | +0.160 % (not opened; nominal 0.1927) | 419 |

v1 retains its adverse numerical failure and its 92,261 origins. The versions change coverage and specification; this table is not a controlled comparison that isolates the effect of each correction. [v1](results_v1.md), [v2](results_v2.md), [v3](results_v3.md) and [v4 with intervals, N and both windows](results_v4.md) retain every sign.

## Conclusion in three sentences

Option-state and options-surface information improve mean RV30 and RV15 forecasts in both families under the registered v3/v4 tests, without implying improvement in every month or independent confirmation in the final 25 sessions. Flow adds a small improvement in the linear family at 15 minutes (+0.623%, 95% CI for the QLIKE difference [0.000335; 0.001932]) and at 5 minutes (+0.256%, secondary): it is positive in all three blocks at both horizons and in all six assets at 15 minutes, **but in only three of the six at 5 minutes**. In trees, B2 does not pass the mean test; the paired median is positive at 15 and 5 minutes, with two-sided p-values 0.0435/0.0038 and Holm 0.0870/0.0096, a secondary that does not replace the primary test.

## What explains the result and what does not

Flow composition carries more weight in the linear representation than gamma exposures: in RV15 of the primary window, the three 5-minute premium proportions (buy, passive and sell) have mean absolute coefficients of 0.250–0.312, compared with 0.00489 for total gamma imbalance; the count of trades with identified direction has mean slope −0.04271; it counts trades, not their signed balance. This does not identify a causal contribution or replace an ablation: the dealer-hedging mechanism remains unproven. [Coefficients by column and horizon](../../artifacts/rp4_closeout_audit/b2_coefficient_summary.csv). Intraday, monthly and training-size profiles are descriptive: the first market hour is distinguished from the first observable period, and the registered block `origin_minute >= 300` from the actual last hour, `>= 330`.

The provider publication interruptions on 2025-05-15 and 2025-09-18 are findings about the measurement instrument. The v3 rule retains zero activity, makes shapes/ratios undefined when there are no trades and adds indicators; it bounds the harm without eliminating it. There remain 412 empty five-minute windows in the primary sample and none in confirmation. They are not excluded to improve the result. In those rows, linear QLIKE rises from 0.103 in B1 to 0.202 in B2 with equal session/asset weights; the repair limits the harm rather than eliminating it.

There is a documented market-structure break: Nasdaq announced the start of Monday and Wednesday expirations for these names on **2026-01-26**. The tape verifies that first presence for all six assets; the jump in cells is observed on 29 January and the first Monday/Wednesday 0DTE on 2/4 February. Mean coverage per origin rises from 20.04 to 23.10 cells before/after the 26th. The confirmation window is entirely in the new regime, with training largely from the preceding regime: it is not a replication under a stable market structure. [Nasdaq notice of 16 January](https://www.nasdaqtrader.com/MicroNews.aspx?id=OTA2026-2) and [daily census and coverage by weekday](../../artifacts/rp4_market_audit/REPORT.md).

The linear penalty is applied to the sum of errors, without dividing by N; the grid is weakly restrictive in large samples and does not guarantee stability of correlated coefficients. B2 selected lambda 0.0001 in 111/419 sessions; pruning removed 88–97 columns, including presence indicators, not 88 constants. Upper bounds were hit by 223/324/302 RV15 forecasts from B0/B1/B2: more hits in richer sets do not by themselves establish the direction of bias. Changing the penalty scale, adapting the grid to the expiration cycle and distinguishing provider unavailability from zero activity remain future work, without rerunning this test.

The period from October 2024 to February 2025 contains 64 evaluated sessions (15.27%), not 84: the early gain from linear B1 at RV15 is negative. Learning time and the market regime change together; the study does not separately identify whether extending warm-up would cause a larger advantage. Negative months are retained. The [profiles by month and training tercile](../../artifacts/rp4_closeout_audit/descriptive_profiles.csv) include October/November 2025, which are negative for linear B2 at both RV30 and RV15. The [descriptive audit](../../artifacts/rp4_closeout_audit/REPORT.md) also distinguishes the 288 origins in the first **observable** hour of tariff week (0.18% of the sample, tree B2 contrast −0.3221 per origin) from the first market hour, which has a different denominator. None is excluded.

The extreme moves in AMZN (31 August, −152/+71 basis points from 14:00 ET; subsequent volume 11 times the median) and TSLA (17 August) were reproduced in one-minute bars and volume. This is internal FMP consistency, not independent price validation; the cause is unidentified.

The final jump secondary uses 419 sessions, not the partial closeout of 418; its label `jump30 > 0` is not a test of a significant jump. Its AUCs near 0.52 do not demonstrate absence of information about economically important jumps. MZ recalibration remains UNVERIFIABLE as a useful result; it does not affect the primary analysis. [Corrected secondary closeout](results_v3_revision2.md).

## Four disclosures

This is the fourth evaluation of the same windows: v1 is the initial design; v2 corrects coverage/capacity/stability; v3 adds imbalance and the empty-window rule; v4 changes the horizon through a predeclared conditional antecedent. RV5 is secondary, not an additional replication; the search across versions is not corrected.

The window from 20 July to 28 August was read once by the Phase 8 bridge under another specification. PIT uses a source-time proxy at 120 s, as in the literature; it does not prove historical availability to the client.

The UW gap 2025-01-25–2025-02-24 is accepted and disclosed, without filling.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

## Documentary revision note

This revision clarifies the construction window and categories of the quoted premium proportions. It preserves the figures, table, windows, decisions and limits of the [original document](RESULTADO_FINAL.md), whose SHA-256 is `6d629b2416601af39a6e7f4fc0f04db1455b6c20ba4c298e7fb21a6ed00b2b19`. The clarification is checked against the [aggregate coefficients](../../artifacts/rp4_closeout_audit/b2_coefficient_summary.csv); its [own receipt](RESULTADO_FINAL_revision_1_receipt.json) identifies the change and both hashes.
