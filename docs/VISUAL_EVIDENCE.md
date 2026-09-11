# A visual reading of the evidence

The figures answer different questions; visual variety is useful only when it
reveals something that another figure hides. All four are deterministic views
of existing public historical aggregates, not new experiments.

| Question | Figure | Read it as |
| --- | --- | --- |
| How large and uncertain is each information increment? | [Effect intervals](figures/public_refresh/effect_intervals.svg) | Saved mean differences with saved 95% percentile bootstrap intervals. The testing decision still uses the declared one-sided sequence. |
| Is the average shared across stocks and models? | [Asset heatmap](figures/public_refresh/asset_heatmap.svg) | Signed mean QLIKE differences, fixed ticker order, one symmetric color scale. Not significance or causal attribution. |
| What is concealed by accumulation? | [Paired session losses](figures/public_refresh/paired_session_losses.svg) | All 419 B1/B2 pairs per family; below equality favors B2. Identical axes, no point exclusions, no fitted trend. |
| How dependent is the gain on assumed availability? | [Timing sensitivity](figures/public_refresh/timing_sensitivity.svg) | Saved linear-model comparisons at three source-time cutoffs, not measured delivery latency or a causal effect per second. |

## Sources and exact transformations

- Intervals: [primary statistics](../artifacts/rp4_v4_b4/primary_statistics.csv),
  `horizon_minutes=15`, `window=primary`, four family/contrast rows. Draw
  `estimate`, `ci_low`, `ci_high`; copy `percent_reduction_mean` for labels.
  The interval is in QLIKE units, not percentage units and not a test inversion.
- Heatmap: [public cumulative asset differences](../artifacts/rp4_readme_figures_v1/cumulative_by_asset_rv15.csv).
  Divide each terminal cumulative B1−B2 difference by 419. Reuse the existing
  producer's reconciliation against global daily losses and the saved per-asset
  estimates in [robustness statistics](../artifacts/rp4_v4_b4/robustness.csv).
  The diverging color scale uses the largest absolute cell as both signed bounds.
- Scatter: [session losses](../artifacts/rp4_v4_b2_rv15/session_losses.csv),
  `loss__<family>__B1` against `loss__<family>__B2`. Existing aggregation first
  averages forecast-origin losses within asset/session, then averages assets
  equally. Do not compute QLIKE from averaged forecasts and actuals: that would
  change the metric. Overlapping dots do not imply missing observations.
- Timing: [60/120-second contrasts](../artifacts/rp4_robustness_public_v1/pit_60_contrasts.csv)
  and [300/120-second contrasts](../artifacts/rp4_robustness_public_v1/pit_300_contrasts.csv).
  Use the saved linear B1/B0 and B2/B1 comparisons, each with its own baseline
  denominator. The line segments connect only the three observed settings; they
  do not estimate values between them. The 120-second cutoff remains primary.
  Denominators are checked against [60-second session losses](../artifacts/rp4_robustness_public_v1/pit_60_session_losses.csv),
  [300-second session losses](../artifacts/rp4_robustness_public_v1/pit_300_session_losses.csv)
  and the primary session-loss table above; the mean paired differences must
  match the saved contrast estimates.
  [Interpretation and complete numerical table](B2_INTERPRETATION.md).

These are the 419 development sessions, not the final 25-session window. The
final window does not confirm the full sequence. None of these visualizations
changes the inferential status or isolates timely trading activity inside B2.

## Why not a volatility surface or a cluster diagram?

An implied-volatility surface maps strike (or moneyness) and expiry to implied
volatility at a specified observation time. It illustrates option state, not
realized-variance forecast performance. QuantLib's
[volatility-surface example](https://www.quantlib.org/slides/dima-ql-intro-2.pdf)
uses those dimensions. A real reconstruction here would require approved quote
snapshots, expiry/strike coverage, time alignment and an explicit interpolation
policy. The public loss aggregates do not contain those inputs. The earlier
cover surface is a labeled schematic, not an empirical reconstruction.

A heatmap is not automatically a cluster analysis. Clustering additionally chooses
variables, distances, normalization and group structure. No such analysis is
needed to show the saved asset differences, so fixed ticker order is retained.

The emphasis on prediction errors and paired comparisons follows the distinction
between fitting and forecast evaluation in Hyndman and Athanasopoulos,
[Forecasting: Principles and Practice, §5.8](https://otexts.com/fpp3/accuracy.html).
This motivates the visual design; it is not external validation of this study.

## Reproduce

Two additional diagrams explain the method and navigation without pretending to
be measurements: [one forecast in time](figures/public_refresh/forecast_timeline.svg)
and [repository route](figures/public_refresh/repository_route.svg). Their
[producer](figures/public_refresh/render_reader_journey.py) uses the existing SVG
style and checks the named repository paths. They contain no simulated market data.
Visible labels use descriptive titles; technical filenames belong in these
reproduction instructions and source links, not inside the figures.

```sh
uv run --frozen python docs/figures/public_refresh/render_reader_journey.py --check
```

From the repository root, using the existing Python environment:

```sh
uv run --frozen python docs/figures/public_refresh/render_reader_diagnostics.py
uv run --frozen python docs/figures/public_refresh/render_reader_diagnostics.py --check
uv run --frozen pytest -q tests/contract/test_reader_diagnostics.py
```

The renderer reuses the repository's SVG style and aggregate reconciliation.
No new plotting dependency, network call, model fitting or private-data access
is needed. SVG text remains selectable and accessible through titles, descriptions
and the README alternatives. Numerical tables remain available alongside figures.
