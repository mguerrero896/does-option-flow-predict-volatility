# English research figures

These six figures retain the saved v1–v4 comparisons, curves, intervals, axes and
sample sizes. The current labels are in English. V4 remains the headline; a figure
comparing earlier versions does not turn reused windows into independent replications.
See the [current results](../../rp4/results_v4.md) for interpretation.

The [translation receipt](translation_receipt.json) records the hashes of five public
CSV inputs, the existing producers, all twelve current SVG/PNG outputs and the
[twelve preserved originals](../../archive/rp4/figure_originals/README.md).
The existing pure renderers first reproduce each original SVG byte for byte; the
adapter then changes text nodes using [versioned English labels](labels_en.json).
It checks every SVG attribute and numeric token. No model fitting, target reads,
new inference or new bootstrap is performed.

From the repository root, in the locked Python environment:

```powershell
uv run --frozen --no-sync python docs/figures/rp4/reproduce_english.py --verify
uv run --frozen --no-sync python docs/figures/rp4/reproduce_english.py --render
```

The first command writes nothing. The second regenerates the six SVGs and checks
them against the receipt. SVG regeneration uses the existing project dependencies.

PNG regeneration uses the original Sharp rasterizer. Set `RP4_FIGURE_NODE` to an
existing Node executable and `RP4_FIGURE_NODE_MODULES` to the existing package
directory containing `sharp`, then run:

```powershell
uv run --frozen --no-sync python docs/figures/rp4/reproduce_english.py --render --png
```

The recorded PNG environment is Sharp 0.35.4, libvips 8.18.6, 96 dpi and one renderer
thread. Exact PNG bytes also depend on the installed fonts. A different renderer
environment fails its recorded-byte check before outputs are written. The SVG
byte check is the portable reproduction route.

The six PNGs were inspected at full figure scale after translation: titles,
legends, interval annotations, dates and footnotes fit within their original
geometry. The complete comparison retains extreme adverse values; the common-axis
summary explicitly marks every point or interval beyond its scale.

RESEARCH_ONLY. NOT INVESTMENT ADVICE. `capital_go=false`.
