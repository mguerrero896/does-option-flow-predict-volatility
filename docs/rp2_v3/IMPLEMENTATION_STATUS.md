# RP2-v3 implementation status

> **Current eligibility:** the timing-and-role rebuild is an historical audit
> record, not a current scientific claim. `data/CANONICAL_STATE.json` records
> `REBUILD_COMPLETE_PIT_V22_BLOCKED`: bar roles and B0/B1 market clocks now fail closed,
> while PIT v2.2 still forbids reconciliation into a current claim.

One row per gate of the registered twelve-gate sequence, in its binding order. A gate is `merged`
only when its own PR carried failing-first tests, the minimal fix, measured before/after
metrics, green `quality` and `hermetic` checks, the local evidence gates, and a review on
its final commit.

| # | Branch | Gate | Status |
| ---: | --- | --- | --- |
| 1 | `docs/rp2-v3-contract` | Freeze the research contract | merged |
| 2 | `fix/rp2-v3-panel-contracts` | Information sets fail closed | merged |
| 3 | `fix/rp2-v3-causal-b0` | Causal, asset-local EWMA baseline | merged |
| 4 | `feat/rp2-v3-contemporaneous-b1` | B1 as contemporaneous option state | merged |
| 5 | `fix/rp2-v3-exact-clock-b2` | B2 dual clocks, exact expiry, 0DTE | merged |
| 6 | `feat/rp2-v3-core-feature-registry` | Core versus rich feature sets | merged |
| 7 | `feat/rp2-v3-fold-local-preprocessing` | Fold-local imputation, common mask | merged |
| 8 | `feat/rp2-v3-qlike-models` | LightGBM aligned to QLIKE | merged |
| 9 | `fix/rp2-v3-session-inference` | Session-level, family-matched inference | merged |
| 10 | `feat/rp2-v3-pipeline-runner` | One reproducible runner | merged |
| 11 | `db/rp2-v3-versioned-results` | Versioned Supabase results | merged |
| 12 | `results/rp2-v3-rebuild` | Rebuild, scorecard, publication | rebuilt; repository delivery recorded by commit and PR history |

## Historical completion record

The timing-and-role run `rp2-v3-20260831-timing-role-remediation` recorded thirteen steps,
every exit code zero, scientific hash `7d544aa334b70ce8…` at commit `cbdd0b5840da`. Its
aggregate bundle, twelve contrasts and treatment-by-coverage factorial are in
[`VERDICT.md`](VERDICT.md). The measurement has no current section-21 classification
because the PIT v2.2 gate remains closed. Earlier published runs remain historical in
[`SUPERSEDED_RESULTS.md`](SUPERSEDED_RESULTS.md).

## 2026-08-31 remediation

- `src/mds650/rp2/bars.py` derives D/V from each session date and rejects a source outside
  its declared role scope; Block 3 now delegates to that shared loader.
- Block 4 uses the shared 120-second cutoff and observes `close[m-3]`; its first valid
  origin is minute 35 and its target remains forward from the origin.
- Block 5 delegates expiry close to the shared XNYS calendar used by B2, including early
  closes. B1 core coverage is 99.34% and all twelve B2 core features are 100% covered.
- The licensed cascade used `--forbid-sealed-cohorts`, completed 13/13 steps and emitted
  new append-only panel pointers, run identity, manifest and Phase 8 dispersion closure.

## Settled decision

The two study windows the repository stated are reconciled. Methodology decision 84, dated
2026-08-21, is the recorded configuration change that makes the frozen partition the RP2
study window, D `2024-08-02..2026-03-23` (389 sessions) and V
`2026-03-24..2026-07-17` (80). The twelve-month freeze is retained for the acquisition
programme it was written for. Measured before deciding: 170 of the 389 development sessions
fall inside the twelve-month window, so adopting it would have discarded 219 of them.
[`STUDY_WINDOW.md`](STUDY_WINDOW.md) carries the reasoning; publication reads the adopted
window from `configs/rp2_v3_study_window.json` and refuses any run that does not match it.

## No longer carried

`role_for` in `src/mds650/rp2/partition.py` has no lower bound, which would have blocked a
twelve-month rebuild: Block 1 enumerates from the start of the tape and labels every
pre-validation session `D`. Decision 84 adopts the partition, which is the window `role_for`
already produces, so the change is not needed and the frozen partition stands. It is recorded
here because it becomes a prerequisite again the moment a narrower window is adopted.

## Standing constraints

- This rebuild read no sealed cohort. At its execution snapshot C, Phase 8 and Phase 9 all
  had read count zero. Phase 8 later consumed its separately authorized exploratory read;
  use `data/CANONICAL_STATE.json` for current counters and never infer them from this record.
- Frozen artifacts are never overwritten. A superseded result is recorded in
  [`SUPERSEDED_RESULTS.md`](SUPERSEDED_RESULTS.md), not deleted.
- No test is weakened to pass. A red test means the cause is fixed.
- Every reported number comes from a real run over the local evidence, never an estimate
  carried over from an earlier run.
