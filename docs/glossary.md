# Glossary of labels and option-market terms

Reference glossary of the labels and option-market terms used in the study. The four tables preserve the supplied wording. The methodology table adds 24 definitions; the reference image preserves the original 36 entries.

**Status: CURRENT.** [Current scientific evidence](CURRENT.md).

[Complete PNG sheet](figures/public_refresh/glossary.png) · [Scalable SVG](figures/public_refresh/glossary.svg) · [Study overview](../README.md)

## Project labels you will see on files and charts

| Label | Meaning in this study |
| --- | --- |
| RP4 | The current historical experiment: does option information improve short-term variance forecasts? Five saved versions, v1–v5. |
| RP3 | A separately registered long-run study with its own rule; its first reading is estimated for January 2029. Not this experiment. |
| RP2 | The earlier validation study (finished August 2026) that found no usable improvement. Its results are history, not current claims. |
| Phase 5 / 8A / 9 | Workstreams of the earlier programme: Phase 5 registered and read the thirty-minute study; Phase 8A recorded a small exploratory bridge; Phase 9 collected the sessions later reused here. |
| v1–v5 | Saved revisions of RP4: v1 diagnosis, v2 data and fitting repair, v3 refined option flow, v4 the fifteen-minute test (headline), v5 the model-combination companion study. |
| B0 · B1 · B2 | The three nested information sets: B0 market history (29 predictors), B1 adds option state (69), B2 adds option flow (138). |
| H1 · H2 | The two ordered tests: H1 asks whether option state beats market history; H2 asks whether option flow beats option state, and only counts if H1 passed. |
| RV30 · RV15 · RV5 | Realised variance over the next 30, 15 or 5 minutes. RV15 is the primary target of v4. |
| Decision 128 / 136 | Numbered entries in the project's decision log: 128 fixed the 1 August 2026 split; 136 registered the four-model average as a secondary candidate. |

Labels identify parts of this project. None of them is an option-pricing concept.

## Option-market terms used in this study

| Label | Meaning in this study |
| --- | --- |
| Option | A contract giving the right to buy (call) or sell (put) a stock at a set price before a set date. Its price reflects how much movement the market expects. |
| Strike | The exercise price written in the contract. Not a forecast or a price target. |
| Expiry · DTE · 0DTE | The contract's end date; DTE is calendar days to expiry; 0DTE expires the same day. |
| Premium | The price paid for the contract, in dollars. "Premium share" is the fraction of premium on one side (buys, sells, out-of-the-money, same-day). |
| Bid · Ask · Aggressor | Best buy and sell quotes. The aggressor is the side inferred to have initiated the trade; it is a proxy, not an observed identity. |
| Implied volatility (IV) | The level of future movement implied by option prices. The surface is IV across strikes and expiries; smile, skew, term slope, risk reversal and butterfly describe its shape. |
| Option state | Measurements of the option market at the forecast time: IV levels and the shape of the surface. Slow-moving, price-based. |
| Option flow | Recent option transactions: counts, premium, buy/sell split, sweeps, multileg trades, same-day contracts and sensitivity flows. Fast-moving, trade-based. |

State comes from option prices; flow comes from option trades. The study tests them in that order.

## Sensitivities, trade types and market words

| Label | Meaning in this study |
| --- | --- |
| Delta · Gamma · Vega | How an option's price responds to the stock price (delta), how delta itself changes (gamma), and how the price responds to volatility (vega). "Flow" versions add these up over recent trades. |
| Dealer gamma | A proxy for the position held by market makers. Hedging that position can move the stock; the study measures a proxy, not actual dealer books. |
| Hedging · Liquidity | Trading to offset an existing risk rather than to bet; how easily a contract can be traded. Both can create trades that carry no forecast. |
| Sweep · Multileg | A sweep executes one order across several exchanges at once; a multileg trade combines several contracts (a spread). Both are recorded trade types, not signals by themselves. |
| Moneyness | Strike relative to the current stock price (strike divided by spot); near one means at the money. |
| Session · Origin | A session is one trading day, 9:30 to 16:00 New York time. An origin is one forecast case: a stock, a day and a minute (10:05 to 15:25, every five minutes; 65 per stock per day). |
| SPY · QQQ | Exchange-traded funds that track the S&P 500 and Nasdaq-100 indices. Used as market controls, and as two extra targets in the eight-asset extension. |
| AAPL AMZN META MSFT NVDA TSLA | Ticker symbols of Apple, Amazon, Meta, Microsoft, Nvidia and Tesla. |
| FMP · UW | Financial Modeling Prep supplies one-minute prices; Unusual Whales supplies the option records. |

Sensitivities and trade types are inputs; the study does not identify who traded or why.

## Measures and checks specific to variance forecasting

| Label | Meaning in this study |
| --- | --- |
| Realised variance (RV) | The sum of squared one-minute log returns over the next interval. It is variance, not its square root (volatility), and not a return. |
| QLIKE (pronounced "cue-like") | The loss used to score variance forecasts: y/f − log(y/f) − 1. It punishes under-forecasting a big move much more than over-forecasting a small one. Lower is better. |
| Persistence · HAR · HARQ | Reference forecasts: persistence repeats the previous session's pattern; HAR combines past variance over several time scales; HARQ adds a measurement-noise adjustment. |
| MAE · RMSE | Mean absolute error and root mean squared error, in variance units. Reported as complements; QLIKE is the declared measure. |
| Linear (log-ridge) · Trees (LightGBM) | The two model families. The linear model fits log variance with a penalty ("shrinkage strength 100" on the receipts); the trees are gradient-boosted with leaves and stopping rounds chosen on earlier data. |
| Point-in-time (PIT) | Only records with a source timestamp at least 120 seconds before the forecast time are allowed. It is a rule on source clocks, not proof of when a client received the data. |
| Purge · Embargo · Warm-up | Training rows whose outcome ends within 60 minutes of validation or forecasting are excluded; the first 60 sessions are reserved to build histories. |
| Block bootstrap · One-sided p | Groups of five consecutive sessions are resampled 9,999 times with a fixed seed; the interval describes the estimated difference and the one-sided test asks whether it improves at the 5 % rule. Holm is the stricter correction for several tests. |
| Placebo · Delay sensitivity | Follow-up checks: shuffled option flow should not look better than nothing; stricter delays (300 and 60 seconds) test the timing rule. |
| Receipt · Manifest · SHA-256 | Files that record inputs, outputs, times and content hashes so that every number can be traced to its file. |

These are the measures behind every percentage in the video; none of them is a trading return.

> Timing clarification: the supplied wording calls both 300 and 60 seconds stricter delays. Relative to the registered 120-second cutoff, 300 seconds is stricter and 60 seconds is less strict. The reference definitions above are reproduced verbatim.

[Timing rule](rp4/specification_v4.md).

## Methodology and evidence status

| Term | Meaning in this study |
| --- | --- |
| Forecast origin | The time at which a forecast is issued. Only information eligible by that time can enter its predictors. |
| Session | One exchange trading date. Primary uncertainty resamples blocks of sessions, preserving the joint composition of assets. |
| Asset-session | One asset on one trading date. The 419-session, six-stock primary sample contains 2,514 asset-sessions; 160,832 intraday origins are not independent observations. |
| RV5 | Realized variance over the next five minutes; a secondary target in the current historical design. |
| RV15 | Realized variance over the next fifteen minutes; the primary target of RP4 v4. |
| RV30 | Realized variance over the next thirty minutes; the target in earlier historical versions, retained for comparison. |
| QLIKE | Variance-forecast loss: for positive observed variance y and forecast h, y/h - log(y/h) - 1. Lower loss is better. Relative improvement is a loss reduction, not a trading return. |
| B0 | price and volatility history. |
| B1 | B0 + option state / implied-volatility surface. |
| B2 | B1 + a heterogeneous option-information block: activity, composition, option-price/IV/spread changes, exposure proxies and empty-window representation. |
| Point-in-time | Eligibility using the information and timestamps available by the forecast origin. The historical 120-second source-time proxy does not establish actual client receipt. |
| Source timestamp | The timestamp attached by the exchange or provider to a record. Its meaning depends on the field; event or creation time does not prove client receipt. |
| Receipt timestamp | The time the client actually received a record, measured by the client. Historical source records alone do not supply this proof. |
| Purge | Exclusion around a chronological split to prevent overlapping information or targets from contaminating training and evaluation. |
| Embargo | A time separation around an evaluation boundary that restricts nearby training observations. The design specifies a 60-minute purge/embargo. |
| Walk-forward | Fit and select using permitted earlier data, then forecast later observations, expanding the training history in time order. OOS fitting does not make the overall design prospective. |
| H1 | The first registered test: whether option state improves B1 relative to B0 in the specified family and sample. |
| H2 | The second registered test: whether flow improves B2 relative to B1. Its formal gate opens only after H1 rejects in that family and sample. |
| Fixed sequence | The ordered H1 then H2 procedure. If H1 fails, a nominal H2 p-value does not constitute a formal rejection. Within-family control is not cross-version control. |
| Bootstrap block | A consecutive group of sessions resampled together to retain temporal dependence. The primary circular bootstrap uses five-session blocks and 9,999 resamples. |
| Historical evaluation | Evaluation on already available historical data. Chronological out-of-sample fitting does not erase earlier knowledge of that sample or specification search. |
| Prospective evaluation | Evaluation under rules fixed before genuinely future eligible sessions arrive. The registered 20, 40 and 335-session reads are dependent cumulative checks, not three independent replications. |
| Exploratory | Evidence used to develop or investigate a hypothesis, including the closed historical extensions. It cannot be promoted retrospectively to independent confirmation. |
| Confirmatory | A claim evaluated under the applicable prior protocol, eligible new evidence and open decision gate. A favorable historical p-value alone does not establish independent prospective confirmation. |

OOS fitting ≠ prospective scientific design. Predictive information ≠ causality. Predictive information ≠ tradability. Statistical significance ≠ economic significance.

B0, B1 and B2 are nested information sets, not necessarily independent economic feeds. The B2/B1 comparison tests for incremental information beyond the implemented B1 representation.

<details>
<summary>Reproduce and verify this reference sheet</summary>

The [versioned text source](figures/public_refresh/glossary.json) drives both this page and the image. The [producer](figures/public_refresh/glossary.py) uses the existing repository figure palette and SVG-to-PNG rasterizer. Verification checks all 36 labels and meanings, the four section titles and footers, and the separate timing note against that source. No wording is shortened to fit the image. No model fits, statistical tests, market-data requests or prospective reads are run.

From the repository root, source and output verification needs Python only:

```sh
python docs/figures/public_refresh/glossary.py --verify
```

To regenerate, use an existing Node.js and Sharp installation. Set `RP4_FIGURE_NODE` to the Node executable and `RP4_FIGURE_NODE_MODULES` to the directory containing the installed `sharp` package. No packages are installed by the producer.

```sh
python docs/figures/public_refresh/glossary.py --render
python docs/figures/public_refresh/glossary.py --verify-raster
```

The [render receipt](figures/public_refresh/glossary.receipt.json) records source and output hashes, dimensions, renderer versions and review status. Code-source hashes normalize CRLF to LF; other inputs and all outputs use exact bytes. The SVG has an intrinsic width of 1676 pixels and a viewBox width of 838. At 838 pixels of available page width, all visible text is at least 20 pixels. The PNG is 1676 pixels wide. SVG files contain no scripts or external resources.

PNG byte reproduction depends on the recorded Sharp and libvips versions and the installed-font environment. Source and SVG verification is independent of the rasterizer. A fresh render resets visual review to pending; inspect the full-size image before recording a new review.

</details>
