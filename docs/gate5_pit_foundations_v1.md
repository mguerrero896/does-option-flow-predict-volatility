# Gate 5 — Foundational PIT assumptions, end to end (v1)

Started 2026-08-17. Code: `scripts/run_gate5_bar_reconciliation.py` (5.1),
`scripts/uw_latency_{collector,verify,reconcile}.py` + `scripts/register_uw_latency_tasks.ps1`
(5.2/5.3). Artifacts: `artifacts/gate5_pit/` and `MDS650_EXTERNAL_ROOT/uw_latency/`.
Zero model reads; zero sealed-cohort access; decision-52 compliant.

## 5.1 — FMP bar semantics (A001): MEASURED, resolved

Cross-provider reconciliation of the same one-minute bars from FMP and the
Polygon-compatible Massive aggregates endpoint (new bounded method
`MassiveProvider.stock_minute_aggregates`), over ten stratified sessions spanning the
C5 (2024), C4 (mid-2025), C6 and 2026 development windows, six outcome assets:

| Alignment | Median of per-cell median relative close differences |
|---|---|
| **Identical labels (same_label)** | **3.1e−06 (near-exact)** |
| FMP shifted +1 minute | 3.66e−04 |

Both providers label one-minute bars identically; same-label agreement is two orders
of magnitude tighter than the shifted convention, with many 2025/2026 cells exactly
equal.
Combined with Gate 3 (reconstructed 30-minute RV matches the frozen `b0_rv_30m_lag`
with log-correlation 1.0000 under shift 0), registered assumption A001 is now an
empirically pinned fact: the pipeline's convention is correct, with an independent
second source across all evaluation eras. A standing tripwire
(`tests/test_gate5_bar_reconciliation_contract.py`) fails the suite if a future
re-acquisition breaks this agreement.

## 5.2/5.3 — UW `created_at` latency campaign: RECONCILED_PARTIAL

**Lifecycle correction dated 2026-09-01.** This section supersedes the 2026-08-18
`RUNNING (unattended)` label and its promise that five reconciled sessions would by
themselves permit a claim upgrade. The machine authority is
`artifacts/gate5_pit/uw_latency_campaign_state_20260901_v1.json`; the aggregate and
anomaly disposition are in the two sibling versioned artifacts. The current inventory
contains 11 collected sessions, six reconciled sessions and five collected but not yet
reconciled sessions.

The latency half produced a measured result. Across all six reconciliations, 2,418 of
2,418 live flow alerts had contract-window tape support (100%). After excluding only the
2026-08-21 contaminated latency distribution, the median of the five session p50 values
is 29.500069 seconds. For 2026-08-17, p10/p50/p90/p99 were
5.001470/29.500069/53.133085/59.831160 seconds. Median-of-session-median latency by
asset was 24.130425–32.370149 seconds. These measurements support the registered
FMP+1-minute rule and +2-minute sensitivity as conservative study cutoffs; they do not
prove provider publication time.

The 2026-08-21 p50 of 4,294.886974 seconds was a collector restart/replay duplication,
classification `COLLECTOR_RESTART_REPLAY_DUPLICATION`, rather than a collector stop,
clock shift or measured provider degradation. Its first-receipt p50 was 34.172432
seconds. It is excluded from latency aggregation under
`EXCLUDE_LATENCY_KEEP_CONTRACT_SUPPORT`; its 636/636 support observations remain in the
contract-window support rate. A ten-times-peer p50 guard now routes this order of
deviation through the existing popup and `logs/UW_LATENCY_ALERT.txt` path.

The permitted `reconciliation.json` inputs do not persist NY-hour aggregates. The
campaign artifact therefore records `NOT_AVAILABLE_IN_RECONCILIATION_JSON` and the
literal reason
`SESSION_RECONCILIATIONS_DID_NOT_PERSIST_NY_HOUR_AGGREGATES; CAMPAIGN_HARVEST_MAY_NOT_READ_LICENSED_ROW_DATA`.
No licensed row data were read to manufacture that missing table.

The backfill/revision half is not identifiable under this design. Every reconciliation
is `PROXY_ONLY_CROSS_CHANNEL`: live observations are aggregate alerts while the later
tape contains individual trades. Backfill remains `None` for
`CROSS_CHANNEL_NOT_IDENTIFIABLE`; revision remains `None` for
`AGGREGATE_ALERT_VS_INDIVIDUAL_TRADE_NOT_COMPARABLE`. More sessions cannot repair a
cross-channel estimand. The count condition (at least five reconciliations) is met, but
the content condition is not; no upgrade to `VALID_UNDER_REGISTERED_TIMING_ASSUMPTIONS`
follows.

## What this retires (and what it does not)

- A001 (bar semantics): retired — measured, two providers, three eras.
- A002 (`created_at` as availability): remains `PROXY_ONLY_CROSS_CHANNEL`. Live receipt
  latency is measured and supports the conservatism of the registered cutoff window,
  but backfill and revision are not identifiable across the two channels. PITV22-C002
  therefore remains `PROXY_ONLY`; historical tapes remain assumption-based.
