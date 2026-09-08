# Glossary

Plain-language definitions for reading *Options Order Flow and Intraday Volatility*. These terms explain the method and its limits; they do not add results or establish investment value.

![Twelve research terms, from volatility and option inputs to uncertainty and prospective replication](figures/public_refresh/glossary.png)

[Scalable image](figures/public_refresh/glossary.svg) · [Study overview](../README.md) · [Current report](rp4/results_v4.md)

<a id="volatility-and-realized-variance"></a>

## Volatility / realized variance

Volatility describes the magnitude of price variation, rather than whether prices rise or fall. Realized variance is a measurement constructed from squared returns over a stated window. Here the target sums squared future one-minute log returns; the square root of variance is a volatility measure. RV15 and RV5 identify the length of the future window in minutes, not annualized volatility or a predicted return.

Sources: [Target definition](rp4/specification_v4.md).

<a id="option-state-and-option-flow"></a>

## Option state / option flow

Option state describes market conditions, including the implied-volatility surface: option-implied volatility across strike prices and expiries. Option flow describes recent trading activity and its composition. In this study, flow is derived from reported trades and direction-based imbalances; it is not a complete record of every submitted or cancelled order. Signed measures are constructed indicators, not direct observations of intermediary inventories.

Sources: [Information sets and inherited features](rp4/specification_v4.md).

<a id="b0-b1-and-b2"></a>

## B0 / B1 / B2: nested inputs

B0, B1 and B2 name sets of predictors, not three model families. B0 contains price and volatility history. B1 retains B0 and adds option state; B2 retains B1 and adds option flow. Comparing B1 with B0 asks about the incremental contribution of state. Comparing B2 with B1 asks about the incremental contribution of flow. The added sets are evaluated within each model family.

Sources: [Nested predictor specification](rp4/specification_v4.md).

<a id="qlike-forecast-loss"></a>

## QLIKE: forecast loss

QLIKE is a quasi-likelihood loss used to compare variance forecasts. For positive observed realized variance y and positive forecast variance f, the registered score is y/f − log(y/f) − 1. Smaller values are better under this score. The reported loss difference is baseline loss minus the richer model's loss, so a positive difference favours the richer model. A percentage loss reduction is relative to baseline forecast loss; it is not a percentage investment return. Trading value would require separate evidence on a strategy, costs and execution.

Sources: [Loss and aggregation rule](rp4/specification_v4.md) · [Reported comparisons and their interpretation](rp4/results_v4.md).

<a id="ridge-and-tree-models"></a>

## Ridge / tree models

Ridge regression fits a linear relationship while penalizing large coefficients, which can reduce instability. The study's ridge model fits log variance and applies its registered transformations and forecast bounds. The tree family uses LightGBM, an ensemble of decision trees that can represent nonlinear relationships and interactions. These are different ways to map predictors to forecasts; an improvement in one family does not establish improvement in the other.

Sources: [Model definitions](rp4/specification_v4.md).

<a id="walk-forward-evaluation"></a>

## Walk-forward evaluation

A forecast origin is the time at which a prediction is made. Walk-forward evaluation moves those origins forward through time: each fitted model uses only its permitted past. Here training expands by session, with model selection and transformations confined to training data. Purge and embargo rules separate overlapping outcome windows around training and evaluation boundaries. Chronological execution controls one source of leakage; it does not make repeated reuse of the same evaluation history independent evidence.

Sources: [Chronological training and temporal controls](rp4/specification_v4.md).

<a id="point-in-time-pit"></a>

## Point-in-time (PIT)

Point-in-time discipline asks what information could have been available at each forecast origin. Exchange execution, provider creation and actual client receipt are different clocks. The study applies a conservative source-time proxy and eligibility rules, not proof of historical receipt by a trading client. A timestamp on an event alone does not establish that the forecaster could have used the record then.

Sources: [Timing claims and limitations](pit_v22_claims_and_limitations.md) · [Availability rule in the study](rp4/specification_v4.md).

<a id="h1-and-h2"></a>

## H1 / H2: ordered questions

In this repository, H1 labels the first comparison: does adding option state reduce mean forecast loss? H2 labels the second: does adding flow reduce loss beyond state? The registered sequence tests H2 formally only after the no-improvement null for H1 is rejected. These are repository labels for ordered questions, not a general convention that H1 means a null hypothesis. If H2 is not opened, a displayed nominal p-value is diagnostic and cannot be treated as a passed formal test.

Sources: [Sequential decision rule](rp4/specification_v4.md) · [Meaning of an unopened test](rp4/results_v4.md).

<a id="p-values-and-confidence-intervals"></a>

## p-value / confidence interval

Under a stated null model and its assumptions, a p-value is the probability of a test statistic at least as extreme as the observed statistic in the tested direction. Here the primary null is no positive improvement in mean loss. A p-value is not the probability that the null is true, nor the probability that a result will replicate. A large p-value does not prove no effect.

A confidence interval (CI) comes from a procedure intended to cover the fixed effect at its stated long-run rate across repeated samples, under the procedure's assumptions. The report uses bootstrap percentile intervals. An interval conveys effect size and uncertainty; its confidence level is not a probability assigned to the truth of a hypothesis or to this one fixed interval.

Sources: [Test direction and interval construction](rp4/specification_v4.md) · [Reported intervals and p-values](rp4/results_v4.md).

<a id="block-bootstrap"></a>

## Block bootstrap

A bootstrap repeatedly resamples the observed data to approximate the uncertainty of an estimate under its assumptions. A block bootstrap resamples groups of adjacent sessions, instead of treating every forecast origin as independent. This study uses circular blocks and preserves the joint asset composition within a session. Block length and dependence assumptions matter; a bootstrap does not eliminate all possible dependence, validate data timing or create fresh observations.

Sources: [Registered bootstrap construction](rp4/specification_v4.md).

<a id="multiple-testing"></a>

## Multiple testing

Testing many questions increases the opportunity for a false positive. A correction or sequential rule controls a stated collection of tests under its assumptions. In the primary study, the H1-to-H2 sequence applies within each family. Separately reported Holm adjustments have their own defined scope; they do not automatically correct every historical version, model choice or adaptive search. A corrected p-value is meaningful only together with the set of tests it covers.

Sources: [Multiplicity scope and limits](rp4/specification_v4.md) · [Results and historical reuse](rp4/results_v4.md).

<a id="prospective-replication"></a>

## Prospective replication

Prospective replication evaluates rules fixed before acquiring the new evaluation observations, under the registered acquisition, analysis and reading conditions. The new evaluation observations are distinct from the reused historical evaluation windows. Training may still use the permitted earlier data, and temporal or cross-asset dependence still requires care. Recording rules and hashes supports traceability; it does not by itself supply an independent timestamp or establish what every person knew. A registered future read is a plan, not a completed confirmation.

Sources: [Prospective protocol](rp4/prospective_confirmation_v1.md) · [Current scope and registered reads](rp4/prospective_confirmation_v1_amendment_3.md).

## Reproduce this glossary

The [versioned text source](figures/public_refresh/glossary.json) drives both this page and the image. The [producer](figures/public_refresh/glossary.py) uses the existing repository figure palette and SVG-to-PNG rasterizer. It reads public documents and creates no model fits, statistical tests, market-data requests or prospective observations.

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
