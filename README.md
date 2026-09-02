# Does option-market information improve intraday volatility forecasts?

[![Tier 1 CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-1a2332)
![Headline claim](https://img.shields.io/badge/global_edge-not_confirmed-e8a33d)

Six large US equities. Every five minutes of the New York session, predict how much the
stock will actually move over the next thirty minutes. Then ask whether knowing what the
options market is doing makes that prediction better.

---

## The answer

**The one-shot PIT v2.2 result is scientifically reportable, but it does not confirm a
global option-information edge.**

The metadata-only holdout-exposure audit is
`NO_VERIFICABLE_DATE_VECTOR_UNAVAILABLE`: the permitted inputs do not contain the
materialized successor holdout dates needed to prove or refute overlap with earlier reads.
It therefore applies no reclassification and does not reopen any outcome.
[`artifacts/target_blind_v22/successor_holdout_exposure_v1.json`](artifacts/target_blind_v22/successor_holdout_exposure_v1.json)
records the inputs, zero-read guard and conditional non-promotion rule.

On the 32-session holdout, the confirmatory Gamma B1a-over-B0 QLIKE contrast is
+0.00817125 [0.00265777, 0.01402423], Holm p=0.00839916. That estimate is still below
the development-frozen MDE of 0.00841614. Gamma B2-over-B0+B1a is -0.00312662
[-0.01392336, 0.00860855], Holm p=0.55954405, versus MDE 0.00667623. Neither registered
contrast reaches its MDE. LightGBM robustness is positive for B1a (+0.00417581) and B2
(+0.00136801), but both remain below the same descriptive MDE references; B2's interval
contains zero. The disposition is `GLOBAL_EDGE_NOT_CONFIRMED`, `capital_go=false`,
`RESEARCH_ONLY`, and `NOT INVESTMENT ADVICE`.

The twelve comparisons below are the historical RP2-v3 context, not the current
confirmatory authority. They separate option *state* (B1 over B0) from recent option
*flow* (B2 over B1), across three model families and two calendar roles.

![Twelve historical contrasts against the threshold each one declared](docs/figures/evidence.svg)

Every comparison registers a detection threshold before it is run, so it cannot be
declared a success after the fact. Two of the twelve beat their own threshold (their
registered minimum detectable effect), and both are discovery option-state contrasts. No flow contrast clears its own
MDE. Discovery LightGBM flow is positive at +0.00052, but its 95% interval
[-0.00013, +0.00111] contains zero and its estimate remains below its 0.00089 MDE.
Validation flow estimates have mixed signs. **That historical bundle is mixed by family
and role, not a universal flow finding.**

The earlier flow exception motivated a sealed question before this timing remediation;
that programme remains frozen rather than rewritten around the updated retrospective run.
[`docs/rp3/PREREGISTRATION.md`](docs/rp3/PREREGISTRATION.md) fixes two hypotheses, on
sessions that mostly did not exist when it was written, to be opened once at 662 sessions
— estimated 2029-01-30.

Two further points a reader should have before going on:

- **Did the option-*state* layer help?** In discovery, yes. It did not hold up under
  validation, so it is not stated as a finding.
- **Did the signal weaken over time?** That cannot be claimed. The data do not show that
  fall, and splitting by date cannot separate a change in the market from simply having
  less data to train on.

---

## When it was tested

![Two retrospective samples, then three sealed tests: one opened, one collecting, one locked until 2029](docs/figures/programme-timeline.svg)

*Bar length is time. The dark bars are measured and reported; the amber card is a test that has never been opened.*

Retrospective work can always be re-run until it agrees with you. The defence against that
is a cohort you are allowed to look at only once, under a protocol written and hashed
before that data existed.

One such read is spent. Phase 8A opened on 2026-08-30 and returned `MIXED_EXPLORATORY`:
the state layer was positive in all four cells with descriptive Holm p below 0.05 in
three, while the flow layer crossed zero in all four and cleared Holm in none. An audit
reproduced the registered inference exactly and found **no aggregation change**. A separate
post-hoc rebuild then corrected the information clock on the same 30 materialized sessions:
only one of eight B1-inclusive primary cells lowered paired QLIKE, although the qualitative
B1-positive/B2-conditional-null pattern survived. Both exercises are descriptive,
**not confirmatory**, and cannot promote anything. Full result in the
[Phase 8A addendum](reports/phase8a_exploratory_bridge_addendum_v13.md).

One cohort is still collecting, and one is sealed until 2029.

---

## What was compared

![Three nested information sets on one shared row mask](docs/figures/information-sets.svg)

Three models see three progressively larger pictures of the same moment, and all three are
scored on exactly the same moments. That is what lets the difference between two steps be
attributed to the information added and to nothing else.

The loss function is QLIKE. The model families are Gamma GLM, ridge-log and
LightGBM-QLIKE. Results are aggregated by trading session before any interval is computed,
because minutes within one session are not independent observations.

One distinction does a lot of work here: knowing *when a fact was true* is not the same as
knowing *when you could have seen it*. Unusual Whales `created_at` is `PROXY_ONLY`, and
Massive SIP timestamps establish when something happened at the source, not when a
subscriber received it. The rules used are in
[`docs/provider_timing_pit_contract_v22.md`](docs/provider_timing_pit_contract_v22.md).

---

## Why you can trust it

![How a measurement becomes an eligible claim, or does not](docs/figures/eligibility-gates.svg)

A number in this repository is not a claim until it passes three gates. Failing one does
not delete the number — it keeps it auditable and marks it as history.

The successor passed scientific-custody validation after one authorized OOS read. It did
not pass the separate edge or capital gates, and the read cannot be repeated. That is the
state this repository publishes, stated in full under
[Governance and current state](#governance-and-current-state).

---

## Where the data comes from

![From licensed provider data to a published, hash-pinned record](docs/figures/data-pipeline.svg)

Provider data is licensed and is not redistributed. Panels are built and evaluated on one
machine; what reaches this repository is aggregate results, schemas and SHA-256 pointers.
Custody and access boundaries are in [`data/DATA_ACCESS.md`](data/DATA_ACCESS.md) and
[`data/GATED_DATA_POINTERS.json`](data/GATED_DATA_POINTERS.json).

That boundary has a consequence worth stating plainly: hosted CI can prove this repository
is internally consistent, but it can never verify a licensed panel, because it cannot see
one. Only a local run can.

---

## Reproducing it

A methodological smoke demo, on synthetic inputs, exercising the primitives only:

```powershell
uv sync --locked
uv run python scripts/run_public_repro_demo.py
```

It does not acquire provider data, build licensed panels, run the cascade or publish
anything.

Hosted CI runs static quality, hermetic tests and scientific contracts against tracked
public inputs; exact commands are in [`docs/ci_contract_v1.md`](docs/ci_contract_v1.md).

Running `pytest` on a fresh clone reports failures from the panel guard, by design: it
fails closed when the licensed panels are absent rather than skipping, because a silent
skip would let an unverified run look green. Each failure names `RP2_PANEL_UNVERIFIED`. To
reproduce what hosted CI reproduces, set the same opt-out CI sets:

```powershell
$env:MDS650_PANEL_GUARD_MAY_SKIP = "1"; uv run pytest tests -q --ignore=tests/unit/test_independent_replication_panel.py --cov=src/mds650 --cov-report=term --cov-fail-under=90
```

The local Tier 2 gate additionally requires licensed evidence and live credentials:

```powershell
uv run python scripts/run_local_evidence_gates.py
```

Boundaries between the two tiers are in
[`docs/reproducibility_contract_v1.md`](docs/reproducibility_contract_v1.md).

---

## Governance and current state

This section is the machine-checked position, kept separate from the finding above: the
finding says what the evidence shows, this says what the project is permitted to claim.

**The current scientific result is the custody-validated PIT v2.2 successor-v2 run.** Its
result SHA-256 is
`ddad159bc02067fd14ef1f7b1c35b9ed02eef26ebd5d19e9e88c5838d6b97775`; its full-log
SHA-256 is `0507ccf5903d46ccd7fee2dc7a535faa8455501e7a1061bafceadd1d8e5f96a3`.
It consumed exactly one OOS read after development-only MDE freeze. Independent custody
validation makes the result eligible to report scientifically, while edge and capital
eligibility remain false.

The prior bundle `rp2-v3-20260831-b1-spot-cutoff-remediation` (scientific SHA-256
`033f2eb6be35e5db06aec2f9e01ef5f3379a8be68b0372087f24e40fa681bea4`) remains
`HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM` for reason
`SUPERSEDED_BY_PIT_V22_SUCCESSOR_V2`.

The authority is [`data/CANONICAL_STATE.json`](data/CANONICAL_STATE.json): one run
manifest, one hash, one eligibility state and its blocking reasons. If any document
disagrees with it, the canonical state wins.

Superseded measurements stay available for audit, never as current findings:

- [`docs/rp2_v3/SUPERSEDED_RESULTS.md`](docs/rp2_v3/SUPERSEDED_RESULTS.md) — what was
  retired, and why.
- [`docs/rp2_v3/VERDICT.md`](docs/rp2_v3/VERDICT.md) — the narrative for the
  corrected-protocol bundle, marked `HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM`.
- [`docs/pit_v22_claims_and_limitations.md`](docs/pit_v22_claims_and_limitations.md) — the
  historical v1 point-in-time boundary and consumed pre-OOS failure.
- [`docs/pit_v22_claims_and_limitations_v2.md`](docs/pit_v22_claims_and_limitations_v2.md)
  — the current successor-v2 contrasts, data-defect disposition and claim limits.

No causal mechanism, formal equivalence, confirmatory discovery or live trading result is
claimed. Residual risks are in the
[threats-to-validity matrix](docs/threats_to_validity_matrix_v1.md).

---

## Repository map

| Path | What is there |
| --- | --- |
| `src/mds650/` | Research and validation code |
| `scripts/` | Producers and verification entrypoints; see [`scripts/README.md`](scripts/README.md) |
| `tests/` | Unit, behavioural, contract and synthetic end-to-end tests |
| `configs/`, `schemas/`, `specs/` | Frozen configuration and machine-readable contracts |
| `artifacts/` | Public aggregates and frozen evidence records |
| `supabase/` | Database schema and access controls; see [`supabase/README.md`](supabase/README.md) |
| `docs/` | Methodology, limitations and history; see [`docs/INDEX.md`](docs/INDEX.md) |
| `reports/` | Deliverables; see [`reports/INDEX.md`](reports/INDEX.md) |

The figures above are generated by `scripts/render_figures.py` from the evidence they
describe, in the palette defined in `scripts/figure_style.py`.

New readers of the code should start with the
[developer guide](docs/DEVELOPER_GUIDE.md) and the
[architecture map](docs/architecture.md).

---

## Scope

Research evidence. Not investment advice, not an order-routing system, not evidence of
live profitability. `capital_go=false`.

[Issues](https://github.com/mguerrero896/does-option-flow-predict-volatility/issues) and
methodological discussion are welcome; boundaries are in
[`CONTRIBUTING.md`](CONTRIBUTING.md), and computational assistance is disclosed in
[`docs/AI_ASSISTANCE_STATEMENT.md`](docs/AI_ASSISTANCE_STATEMENT.md).

See [`CITATION.cff`](CITATION.cff), [`LICENSE`](LICENSE) for the MIT licence covering
project-authored material, and [`SECURITY.md`](SECURITY.md) for private vulnerability
reporting.
