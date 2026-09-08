# Existing cumulative loss aggregate

[cumulative_by_asset_rv15.csv](cumulative_by_asset_rv15.csv) contains 419 saved
session dates and twelve cumulative QLIKE differences: six stocks for each of
the linear and tree model families. The difference is the daily mean loss of the
option-state model minus that of the model adding option flow. Positive values
favour adding flow. Values are in cumulative QLIKE units, not percentage returns.

The file was copied byte for byte from an existing figure aggregate. No private
producer, checkpoint, granular target or forecast file was executed or opened to
create this public copy. The [import receipt](import_receipt.json) records its
SHA-256, six-decimal precision and comparisons with existing public loss controls
and per-stock endpoint estimates. Those checks authenticate this aggregate and
its consistency; they do not reconstruct the private per-origin calculations.

The [public figure generator](../../docs/figures/public_refresh/render_readme_figures.py)
preserves all dates and provides SVG/PNG output with a shared vertical scale.
Its [instructions](../../docs/figures/public_refresh/README.md#figures-for-a-first-reading)
describe verification and rendering without new scientific evaluation.
