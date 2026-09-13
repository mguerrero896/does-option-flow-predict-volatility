# RP4 activity without IV: development contract v1

Defined before evaluation, 2026-09-13. RESEARCH_ONLY; NOT INVESTMENT ADVICE;
capital_go=false. This is an opt-in research variant, not a correction of the
published RP4 estimate and not a change to its frozen producers or manifests.

## Scope and hypothesis

Hypothesis: valid observable activity excluded solely by IV eligibility may add
information about RV15. No gain is assumed. Change exactly eight existing columns:
`b2_{5m,30m}_{trades,contracts,size,premium}`. Keep every other column, including
Greek flows, IV changes, shares, intensity and empty-window indicators, on its
original IV-eligible population. In particular original empty-window indicators
still describe that original population, not the new activity population.

The source is the RP4 v2 `materialize_iv.option_features` path inherited by v3/v4,
not phase5 compact B2. Its reader applies IV [0.01,5], then v2 tightens this to
[0.03,3] for the whole flow tape. That rule was deliberate for the original
experiment. This variant does not edit it or any hash-pinned historical source.
The new wrapper defaults to the original call and requires explicit
`independent_activity=True` to overlay the eight activity columns requested.

## Population, clocks and units

Input is a single asset/session tape already provided by an authorized caller.
Activity accepts null, nonfinite and out-of-range IV without replacing its value.
Require finite positive size and strike, finite nonnegative premium, nonnull expiry,
call/put type, and UTC-aware nonnull execution/creation timestamps with creation
not before execution. Exclude expired contracts and other assets. Preserve the
existing session/available-underlying-price filter through `_in_session`; no
new quote-quality or IV requirement is added. Invalid records are excluded from
all four activity totals, not converted to zero-valued trades. Size is contract
units, premium is the supplied trade premium in USD, trades counts rows, and
contracts counts distinct (expiry,strike,option_type) tuples. No additional event
deduplication is introduced relative to the original flow reader.

At origin t, cutoff c=t-120 seconds; include executed_at in [c-window,c] and
created_at <= c. The lower bound is inclusive, matching the original feature
windows (not the separate half-open scorecard counting buckets). Reject negative
latency before selection. Timestamps use explicit UTC microseconds. Creation time
remains an availability proxy, not historical client receipt. Empty windows have
zero activity only when the session has at least the existing 50 valid prints;
sparser sessions remain null. Inputs, keys, origins, targets and IV components
are not modified. Output preserves requested column order.

## Validation and evaluation boundary

Use synthetic tests for invalid IV with valid activity; invalid activity; both
time boundaries, stale executions and future creation; sparse/empty distinction;
exact default/baseline and non-activity invariance. Compare the all-valid case
against the original producer. Do not run frozen historical entrypoints: their
hashes and one-shot authorizations remain intact.

No data or model evaluation has been authorized by this contract itself. A future
comparison must keep B0/B1, targets, origins, preprocessing, estimator and tuning
budget equal and use a common eligible sample. Any already-exposed development
data require identifiable authorized source and split receipts; label such results
exploratory. Never reopen a sealed cohort or call a rerun of RP4 a new confirmation.
Otherwise register a new prospective comparison before collecting/evaluating it.

Development 2024-08-02 through 2026-07-31 is already exposed: specification_v5.md
explicitly records the fifth historical read. The new authorized comparison would
therefore be exploratory, paired variant-minus-original B2 QLIKE at RV15, using
the same ridge procedure and common sample, six original assets and 60-session
warmup. Report MAE/RMSE and paired session-level uncertainty as secondary measures;
do not select features or alter this population after seeing losses. Exclude the
25 later historical sessions and every prospective cohort. No extra one-shot read.

Execution is pending identifiable, hash-verifiable development tape/session/bar
receipts. This isolated public projection has no `private-input` directory; the
frozen materializer's redacted OLD_ROOT and manifest hashes are not a usable
source mapping. Do not search sealed/raw directories to guess that mapping. The
minimum intervention is an authorized manifest/path mapping for the exposed
development inputs; then verify custody and finalize a separate release before
materialization. Estimate runtime before substantial computation after measuring
an authorized target-free development shard; no full-run duration has been measured
for this variant. A new prospective trial needs its own future cohort and power
calculation, not assignment to the existing protected cohort.

## Running the verified code

Import `activity_without_iv.option_features` in place of the historical function
only in a new authorized caller, and pass `independent_activity=True`. It accepts
the same in-memory raw/base/grid/columns arguments and filtered flag. It performs
no provider calls or file writes. `activity_features` is also available to compute
the eight-column keyed overlay without rebuilding the baseline. There is no new
CLI that could accidentally reopen historical entrypoints.

With the existing project Python environment, put `src`, `scripts`,
`artifacts/rp4_code`, and `artifacts/rp4_v2_code` from this checkout on PYTHONPATH:

```powershell
python -B -m pytest artifacts/rp4_v2_code/test_activity_without_iv.py artifacts/rp4_v2_code/test_materialize_iv.py -p no:cacheprovider
```

Initial focused result: 26 synthetic tests passed in 1.75 seconds; Ruff checks
passed. This demonstrates implementation behavior, not predictive improvement.
The activity scan is linear in visible tape rows per origin; scale optimization
requires profiling before a full history run. Original session sparsity threshold
is retained and is a full-session coverage rule, not a real-time coverage guarantee.

## Navigation provenance

Consulted active second brain through local mcp_query.py: accepted f0943e5a65a7,
1,311 permitted tracked files, 710 Python files, 328 documents; same as candidate
HEAD. Dedicated new MCP was unavailable in this session. Static snapshot excludes
WIP, raw and sealed data. Direct source/caller inspection confirmed the RP4 path
and its hash pins; no source or index was refreshed.
