# Lean operational control board

## Data custody

Show only the frozen-artifact count, how many are physically present, how many remain
externally gated or withdrawn, the gated-file count, sealed-read count and last Tier 2
result. The authoritative repository producer is `scripts/generate_canonical_state.py`,
which derives
the repository custody values from `data/FROZEN_ARTIFACTS.json`,
`data/PUBLIC_METADATA_REDACTIONS.json` and `data/GATED_DATA_POINTERS.json`; the Tier 2
runner is `scripts/run_local_evidence_gates.py`. For Phase 9, display only the
`session_manifest.json` and `counter.json` metadata written by `scripts/phase9_collect.py`
and checked by `scripts/phase9_verify.py`. A red count or hash stops the board. Never copy
licensed rows into it and never infer custody from a filename.

## Collector health

Show two signals per collector: task ready and last capture complete. The authoritative
live checker is `scripts/verify_scheduled_tasks.py`; it already validates task presence,
action target, working directory, next trigger, exit code and the required disabled Phase
8 tasks. Capture status and literal failures come from `scripts/uw_latency_verify.py` for
UW and `scripts/phase9_verify.py` for Phase 9. Keep Windows Task Scheduler as the runtime
source; the board reads it but never registers, restarts or repairs tasks. Do not use the
stale `08:10` entry in `artifacts/phase9/activation_record.json`; the governing task
producer and decision 97 use `09:45`.

## Active experiment

Show Phase 9 only: lifecycle state, complete sessions out of 60, scored sessions out of
36, sealed reads, and next permitted action. `scripts/phase9_collect.py` produces the live
counter/manifests and `scripts/phase9_verify.py` validates them without reading outcomes;
`docs/phase9_total_contribution_protocol_v1.md` governs the method. Present Phase 8 as
closed after its consumed read, even though the canonical history retains its protocol.
Do not turn a scheduled task, a complete sample count or an operator note into evaluation
authority. Do not display the conflicting audit hash in
`docs/phase9_academic_reporting_policy_v2.md` until its governing producer corrects it.

## Current claim status

Show exactly four fields from `data/CANONICAL_STATE.json`: scientific-result eligibility,
edge-claim eligibility, `capital_go`, and the current decision/status. The authoritative
producer is `scripts/generate_canonical_state.py`, bound to the current scorecard, custody
audit and claim ledger; `STATUS.md` is display-only. Render the existing boundaries
verbatim: `RESEARCH_ONLY`, `NOT INVESTMENT ADVICE`, no confirmed global edge and
`capital_go=false`. A future board should be one deterministic Markdown/JSON projection of
these producers, not a new dashboard service or second state store.
