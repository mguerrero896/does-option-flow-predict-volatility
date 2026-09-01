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

**Lifecycle authority refreshed 2026-09-02; hourly-latency correction dated 2026-09-01.** This section supersedes the 2026-08-18
`RUNNING (unattended)` label and its promise that five reconciled sessions would by
themselves permit a claim upgrade. The machine authority is
`artifacts/gate5_pit/uw_latency_campaign_state_20260902_v3.json`; the aggregate and
anomaly disposition are in the two sibling versioned artifacts. The current inventory
contains 12 collected sessions, six reconciled sessions and six collected but not yet
reconciled sessions. All 2026-09-01 artifacts and the 2026-09-02 v1/v2 pairs remain
immutable historical snapshots; v3 records the later capture-report arrival without
editing them.

The latency half produced a measured result. Across all six reconciliations, 2,418 of
2,418 live flow alerts had contract-window tape support (100%). After excluding only the
2026-08-21 contaminated latency distribution, the median of the five session p50 values
is 29.500069 seconds. For 2026-08-17, p10/p50/p90/p99 were
5.001470/29.500069/53.133085/59.831160 seconds. Median-of-session-median latency by
asset was 24.130425–32.370149 seconds. These session-level measurements alone do not
establish that a fixed receipt buffer holds at the opening.

The hourly overlay computes local `receipt_utc - created_at`, assigns the NY hour from
`receipt_utc`, retains only records whose `start_time` belongs to that NY session, and
keeps the first valid receipt per record. It contains 1,768 first receipts from the five
clean sessions; 2026-08-21 remains excluded under its registered disposition. The full
receipt-hour distribution is:

| Receipt hour NY | n | Sessions | p10 s | p50 s | p90 s | p99 s | >60 s | >120 s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 9 | 406 | 5 | 4.046290 | 33.500327 | 54.831990 | 60.216898 | 6 | 0 |
| 10 | 514 | 5 | 5.778457 | 29.608568 | 54.746811 | 60.485070 | 8 | 0 |
| 11 | 258 | 4 | 6.831178 | 34.455436 | 56.970972 | 60.603583 | 11 | 0 |
| 12 | 180 | 4 | 5.254701 | 28.490399 | 49.429447 | 59.799363 | 2 | 0 |
| 13 | 157 | 4 | 7.326196 | 31.143349 | 54.591506 | 59.547908 | 0 | 0 |
| 14 | 95 | 4 | 5.153326 | 29.264273 | 55.971078 | 148.023208 | 2 | 2 |
| 15 | 156 | 2 | 4.414924 | 24.000146 | 52.999946 | 59.177703 | 2 | 0 |
| 16 | 2 | 2 | 24.363917 | 27.979962 | 31.596006 | 32.409616 | 0 | 0 |

**Opening-cutoff answer.** The opening hour contains 406 first receipts across all five
clean sessions. Six exceed 60 seconds, 6/406 (1.48%), and its p99 is 60.216898 seconds;
0/406 exceed 120 seconds. Therefore the registered 60-second UW availability buffer —
the B2 timing leg used alongside the separately measured FMP+1-minute bar convention —
does not hold as a strict conservative bound at the NY opening in this sample. The
120-second sensitivity does hold at the opening in these five sessions, but not as an
all-day strict bound: two of 95 receipts in hour 14 exceed 120 seconds. Five sessions and
406 opening receipts are sufficient to falsify a zero-exceedance claim in the observed
sample, not to certify a universal future-session guarantee. This changes no historical
panel, mask, estimate or verdict; `created_at` remains a proxy rather than proven client
availability.

The hour-by-asset table is published only where both `n >= 30` and at least three
sessions contribute. At the opening this supports AAPL (54), META (36), NVDA (180) and
TSLA (87). AMZN (25 across five sessions) and MSFT (24 across four) are reported as
insufficient rather than assigned unstable quantiles. The v2 artifact contains every
supported hour-by-asset quantile and every insufficient-cell count.

The 2026-08-21 p50 of 4,294.886974 seconds was a collector restart/replay duplication,
classification `COLLECTOR_RESTART_REPLAY_DUPLICATION`, rather than a collector stop,
clock shift or measured provider degradation. Its first-receipt p50 was 34.172432
seconds. It is excluded from latency aggregation under
`EXCLUDE_LATENCY_KEEP_CONTRACT_SUPPORT`; its 636/636 support observations remain in the
contract-window support rate. A ten-times-peer p50 guard now routes this order of
deviation through the existing popup and `logs/UW_LATENCY_ALERT.txt` path.

The hourly table is a custody-safe aggregate derived from the licensed observation logs;
no provider row, identifier, price, premium or external absolute path is emitted. Exact
source hashes bind the aggregate to the five logs. A live freshness contract regenerates
the snapshot from the authorized `uw_latency/sessions` inventory and fails on any byte
divergence. Because the campaign is still moving, drift requires a new dated immutable
snapshot; neither v1 nor v2 is overwritten.

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
  latency is measured, but the 60-second buffer is not a strict opening bound in the
  observed sample; the 120-second sensitivity has no opening exceedance but has two
  hour-14 exceedances. Backfill and revision remain non-identifiable across the two
  channels. PITV22-C002 therefore remains `PROXY_ONLY`; historical tapes remain
  assumption-based.
