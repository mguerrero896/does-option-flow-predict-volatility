# RP3 execution guide — operating the sealed program until its single read

Written for a programmer who has never seen this repository. Read
`docs/rp3/PREREGISTRATION.md` first (SHA-256 of the committed file, LF line endings:
`66906a88b0d8ff76d9bbc6556e0aa64e32de494254d2ebdccc49140fce7f77e7`); this guide only
explains how to operate what that document commits to. Decision 93 in
`docs/methodology_decisions.md` records why the program exists.

## What is already frozen, and where

| Piece | File | Integrity |
| --- | --- | --- |
| Preregistration | `docs/rp3/PREREGISTRATION.md` | hash pinned by `tests/contract/test_rp3_program_guards.py` |
| B2 index (theta) | `artifacts/rp3/b2_index_theta.json` | self-hash + reproduction test (`tests/unit/test_rp3_b2_index.py`) |
| Sizing (N = 662, read ≈ 2029-01-30) | `artifacts/rp3/sizing.json` | self-hash + coherence tests (`tests/unit/test_rp3_sizing.py`) |
| Frozen forecasters (B1 and B1+index, LightGBM) | `artifacts/rp3/frozen/` | manifest self-hash + per-file SHA-256, round-tripped at freeze time |
| Look counter | `artifacts/rp3/look_counter.json` | pinned to 0 until the read |

The frozen models were trained by `scripts/rp3_freeze_forecasters.py` on every session
through 2026-07-17 (469 sessions, 184,632 origins) and refuse to score anything at or
before that date: `FrozenForecasters.predict` raises `RP3_EVAL_WINDOW_VIOLATION` unless
the caller explicitly re-scores history (only the freeze's own round-trip does).

## The operating cycle (weekly, or any cadence — the cadence is not load-bearing)

1. **Acquire** the new sessions' raw inputs with `scripts/rp3_acquire_batch.py`
   (authorized by the owner 2026-08-25). It reuses the two verified provider cores
   unchanged — the UW full-tape ZIP route from `scripts/download_calibration_20d.py`
   and the FMP one-session-per-request pattern from `scripts/acquire_gate3_dev_bars.py`
   (`docs/reference/provider_http_reference.md` is binding for auth and endpoints) —
   and lands the tape under `<data-root>/tape/full_tape_eval/date=YYYY-MM-DD/` and the
   bars in `<data-root>/data/fmp/underlying_1min_eval.parquet` (default data root
   `<DATA_ROOT>/rp3`), for the six frozen targets (AAPL, AMZN, META, MSFT, NVDA, TSLA)
   plus SPY and QQQ. Three fail-closed guards, all pinned by
   `tests/unit/test_rp3_acquire_batch.py`: sessions strictly after 2026-07-17, only
   completed sessions, and — decisive for the first batch — the **Phase 8 cohort seal**:
   sessions 2026-07-20..2026-08-28 are the Phase 8 prospective cohort
   (`docs/phase8_bridge_protocol_v2.md`, separate one-shot authorization required), and
   `sealed_cohorts_read = 0` admits no acquisition-time exception. The acquirer refuses
   them until the calendar passes the read date **and** receives the self-hashed result
   written by the evaluator after the authorized read. A boolean operator attestation is
   insufficient. The first legal batch is therefore 2026-08-30 or later, and one run can
   process the whole backlog after that result exists:

   ```
   uv run python scripts/rp3_acquire_batch.py --phase8-result <result.json>
   ```

   Two operational facts an adversarial review made explicit, both enforced in code
   and pinned by tests: **the clock is New York's, not the machine's** (this machine
   runs at UTC+10, where local midnight is mid-morning on the NYSE floor — a session
   counts as complete only when the America/New_York date has moved past it; the
   clock lives in `mds650.exchange_clock` and
   `tests/contract/test_exchange_clock_contract.py` fails if any RP3 surface ever
   reads the machine clock again; the machine's own timezone is never changed — local
   automation like the Phase 8 watchdog's 20:00 trigger depends on it). In local
   terms: the New York date moves past the read date at **14:00 Sydney time on
   Sunday 2026-08-30**, the first moment the command above unlocks. And
   **the two scripts' `--data-root` differ by design**: the acquirer's root IS the
   rp3 subtree (`<DATA_ROOT>/rp3`), while the batch adapter takes its PARENT
   (`<DATA_ROOT>`) and reaches the same files through its relative paths
   (`test_the_two_scripts_data_roots_compose` pins the composition). All three
   session guards also hold in depth — inside both acquisition legs, not only at
   planning — and idempotency is verified, not trusted: tape reuse re-hashes the
   recorded ZIP, bar reuse requires the store to exist, and a corrupt leftover ZIP
   or manifest is discarded and redone rather than wedging its session.
2. **Build the session panels** with the batch adapter, which exists:
   `scripts/rp3_build_eval_panels.py --data-root `<DATA_ROOT>` --batch-id rp3-batch-YYYYMMDD`.
   It drives blocks 3–4 by import over the batch's own bar stores
   (`mds650.rp3.eval_inventory.EVAL_BAR_SOURCES`) and blocks 5–6 as subprocesses through
   their `--inventory` flag, window-guarding every session (`RP3_EVAL_WINDOW_VIOLATION`
   at or before 2026-07-17) and writing everything under the gitignored
   `artifacts/rp3/eval_panels/<batch-id>/`. Run `--dry-run` first: it validates the whole
   wiring — tape partitions, bar stores, builders — without reading a data page. The
   adapter's target set is imported from `mds650.rp2.panel.TARGET_ASSETS` (it briefly
   restated the tuple with GOOGL where TSLA belongs; the import and a drift test now
   make that class of error impossible). With acquisition authorized and step 1's
   script in place, what gates the first real batch is only the Phase 8 calendar above.
3. **Score** the batch into the bank with `scripts/rp3_score_batch.py`, which exists:
   `uv run python scripts/rp3_score_batch.py --batch-id rp3-batch-YYYYMMDD`. It
   reproduces the exact RP2 merge (`load_merged_panel`), keeps only the preregistered
   evaluation universe (`common_evaluation_mask` — the block-10 common mask), scores
   every origin with the frozen models (`load_frozen(...).predict`, hash-verified,
   index computed internally), computes `signed_return_120` from the batch's own bars
   with the ext1 recipe that defined it (equivalence pinned by test), and appends one
   row per origin — keys, index value, both forecasts, realized `rv30`,
   `signed_return_120`, batch id — to the **evaluation bank**:
   `artifacts/rp3/evaluation_bank/` (gitignored; licensed-derived granular rows live
   only locally and in the gated Supabase bucket, like the fifteen gated files).
   Its guards, all pinned by `tests/unit/test_rp3_score_batch.py`: the look counter
   must read 0; duplicated origins across batches are refused (they would inflate the
   N = 662 trigger); reuse is verified by parquet hash AND input-panel hashes
   (`RP3_BANK_INPUT_DRIFT` if the panels were rebuilt under the same batch id);
   sessions must be real, completed trading dates on the New York clock, present in
   the batch's bar store; a non-default `--bank-root` inside the repo is refused; one
   writer at a time (`.lock`); and the module cannot even import the comparison
   machinery, nor call an aggregation (QLIKE, contrasts, mean/sum/corr) — the
   anti-look rule as an `ast`-level tripwire.

   **The census toward N = 662** (read from `artifacts/rp3/sizing.json`, never
   restated) counts only batches whose PASS manifest still hash-matches its parquet —
   a stray or tampered file in the bank directory contributes nothing. **Recovery
   from a crash mid-banking**: a parquet without its manifest is an orphan the next
   run refuses by name (`RP3_BANK_ORPHAN_PARQUET`); its rows were never manifested,
   so delete it and re-run — that is the documented, safe procedure.
4. **Do not aggregate.** No one computes, previews, or partially aggregates the
   confirmatory contrasts before the read. The look counter stays at 0 and its guard
   runs in every CI pass.

## The single read (estimated 2029-01-30)

When the bank holds **662 evaluable sessions** (`artifacts/rp3/sizing.json` is the
authority; its `session_bank.read_date` is an estimate, the count is the trigger):

1. Confirm `look_counter.json` reads 0 and the guards pass.
2. Compute H1 exactly as preregistered: paired QLIKE contrast, session-clustered, between
   the frozen B1 and B1+index forecasts, one-sided, α = 0.05.
3. If and only if H1 rejects, compute H2 (directional information of the index for
   `signed_return_120`), α = 0.05, per the fixed-sequence gate.
4. Set the counter to 1 **in the same commit** that publishes the read's artifacts, and
   publish the outcome — positive, null, or negative — with the same prominence.

## What must never happen, and what watches for it

| Forbidden | Watcher |
| --- | --- |
| Editing the sealed preregistration | hash pin in `test_rp3_program_guards.py` |
| Retraining, re-tuning, or swapping the frozen models | manifest + per-file SHA-256 checks |
| Scoring pre-window sessions into the bank | `RP3_EVAL_WINDOW_VIOLATION` in `predict` |
| A confirmatory look before N = 662 | look-counter pin, moved only by the read's own commit |
| Committing bank rows to the public mirror | `.gitignore` rule + the gated-publish tripwire's bank-shape rule (`BANK_SHAPE_COLUMNS` in `tests/test_gated_publish_contract.py`: any tracked parquet/CSV carrying `b1_plus_index` beside `signed_return_120` fails, wherever it sits) |
| Reading any sealed RP2 cohort | unchanged programme rule; RP3 touches only post-window data |

## If something breaks

A failed guard is a recorded fact, not an emergency to be tidied: fix the cause, never
the assertion. If the frozen artifacts are ever lost locally, they are recoverable from
any clone (all are committed); if a hash mismatch appears, the committed history is the
authority and the working tree is what drifted.
