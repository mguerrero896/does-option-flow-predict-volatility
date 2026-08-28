# RP3 historical-reach probe (A5)

**Question.** Can the RP3 training window extend backwards past `2024-08-02`?
The current start was adopted as an Unusual Whales restriction; if the RP2-v3
B2 signal were built from the Massive tape (deep history), that limit might no
longer bind.

**Answer, measured: no.** The premise fails on provenance. The option tape the
v3 pipeline reads — the same tape B1 and B2 are derived from — is the
**Unusual Whales full tape** (`/api/option-trades/full-tape/{day}`, see
`scripts/download_calibration_20d.py:76`; `scripts/rp2_block6_flow_panel.py`
reads it through `artifacts/rp2_block1_partition/inventory.jsonl`), not
Massive. Its oldest partition on disk is `2024-08-02`, which coincides with the
oldest *non-empty* day UW served when entitlement was probed
(`artifacts/api_audit/window_probe_20260720/probe_summary.md`: entitled back to
2023-08-18, oldest non-empty events ~2024-08-02). The floor is the provider's
own data start, not merely our subscription — there is nothing earlier to
acquire from UW, and nothing earlier exists on disk.

Probe date: 2026-08-24. Method: read-only. Parquet footers only (row-group
statistics via pyarrow) for the single-file bar stores; date-partition
directory names for the tape stores. No data pages were loaded; no sealed
cohort was read (only backward reach — minima — is reported here).

## Option-events tape (input to B1 surface and B2 flow)

Five date-partitioned stores under `<DATA_ROOT>`, layout
`<root>/date=YYYY-MM-DD/asset=<A>/events.parquet`. The temporal "column" is the
`date=` partition name; minima below are **measured** from directory listings.

| Store | Path (root) | Temporal key | Measured min date |
| --- | --- | --- | --- |
| b1v3_confirmation | `<DATA_ROOT>/b1v3_confirmation/data/option_events` | `date=` partition | **2024-08-02** |
| b1_diagnostic_replication | `<DATA_ROOT>/b1_diagnostic_replication/data/option_events` | `date=` partition | 2024-12-10 |
| independent_replication_30 | `<DATA_ROOT>/independent_replication_30/data/option_events` | `date=` partition | 2025-02-25 |
| phase6 | `<DATA_ROOT>/phase6/data/option_events` | `date=` partition | 2025-07-07 |
| development_2026 | `<DATA_ROOT>/data/option_events` | `date=` partition | 2026-03-24 |

The on-disk minima equal the minima recorded in the run's inventory
(`artifacts/rp2_block1_partition/inventory.jsonl`): the stores hold nothing
older than what the run already used. Overall tape floor: **2024-08-02**.

## One-minute bar stores (input to B0 and to the RV targets)

Single parquet files, FMP-sourced, listed in `bar_sources_sha256` of
`artifacts/rp2_v3/rp2-v3-20260824-remeasure/input_manifest.json` and resolved
against `<DATA_ROOT>` per `src/mds650/rp2/bars.py::BAR_SOURCES`. Minima below are
**measured** from parquet row-group statistics (all row groups carried
complete min/max statistics; row counts from the footer).

| Store | Path | Temporal column | Measured min (UTC) | Rows |
| --- | --- | --- | --- | --- |
| ohlcv_repair (D) | `<DATA_ROOT>/data/fmp/rp2_ohlcv_repair/underlying_1min_repair.parquet` | `bar_start_utc` | 2024-10-28 13:30 | 138,239 |
| phase6_180d (D) | `<DATA_ROOT>/phase6/data/fmp/underlying_1min_180d.parquet` | `bar_timestamp_raw_utc` | 2025-07-07 13:30 | 558,697 |
| gate3_dev80 (V) | `<DATA_ROOT>/data/fmp/gate3/underlying_1min_dev80.parquet` | `bar_start_utc` | 2026-03-24 13:30 | 187,197 |
| ext3_missing (D) | `<DATA_ROOT>/data/fmp/rp2_ext3/underlying_1min_ext3.parquet` | `bar_start_utc` | **2024-08-02 13:30** | 352,618 |
| validation_market (V) | `<DATA_ROOT>/data/fmp/rp2_validation_market/market_1min_validation.parquet` | `bar_start_utc` | **2024-08-02 13:30** | 286,740 |
| volume repair overlay | `<DATA_ROOT>/data/fmp/rp2_volume_repair/minute_volume_repair.parquet` | `bar_start_utc` | 2025-02-25 20:33 | 899 |

Overall bar floor on disk: **2024-08-02**. No store cited by the manifest
reaches earlier.

## Implication for growing D backwards

- **The tape cannot go back.** B1 (surface) and B2 (flow — the RP3 primary
  contrast) are derived from the UW full tape, whose oldest non-empty day is
  ~2024-08-02 by the provider's own data, not by our window choice. There is
  no earlier UW tape to buy or download. This is measured for entitlement as
  of the 2026-07-20 probe; that the provider has since backfilled 2023-2024
  history is possible in principle but **not probed**.
- **Bars barely could.** FMP one-minute bars were verified non-empty to 730
  days back from 2026-07-20 — i.e. to about 2024-07-21, roughly two weeks
  before the current start (inferred from the probe depth, not re-measured
  here). Even if acquired, only B0 and the RV targets could extend; B1 and B2
  could not accompany them, so any backward extension would train the primary
  contrast on origins where its treatment features simply do not exist.
- **Massive is not a substitute tape today.** The window probe shows Massive's
  deep options history alive (an expired-2017 reference returned rows) and its
  stock minute bars *not* entitled. Rebuilding B1/B2 from a Massive options
  tape would be a provider migration — new schema, new trade-side semantics
  (B2's direction comes from the UW per-trade `ask_side` tag), new
  reconciliation gates — not a window extension. That is a separate program
  decision, out of scope for RP3.

**Bottom line.** With the stores the sealed run actually cites, `2024-08-02`
is a hard floor: the training window for Phase B cannot extend backwards
without either a provider backfill that does not currently exist (UW) or a
provider migration that changes what B2 *is* (Massive). RP3 should keep the
frozen start.
