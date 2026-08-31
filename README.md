# Does option-market information improve intraday volatility forecasts?

[![Tier 1 CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-1a2332)
![Headline claim](https://img.shields.io/badge/headline_claim-none_eligible-e8a33d)

Six large US equities. Every five minutes of the New York session, predict how much the
stock will actually move over the next thirty minutes. Then ask whether knowing what the
options market is doing makes that prediction better.

---

## The answer

**Almost never — and the one exception is why a sealed program exists.**

Eleven of the twelve headline comparisons show no gain from adding recent option *flow*
once contemporaneous option *state* is already in the model.

![Twelve contrasts against the threshold each one declared](docs/figures/evidence.svg)

Every comparison registers a detection threshold before it is run, so it cannot be
declared a success after the fact. Three of the twelve beat their own threshold. Two of
those are option state. The third — the amber one — is option flow, and it is the reason
the rest of this repository exists.

That cell estimates **+0.00060** against a threshold of **0.00056**, with a 95 % interval
of [+0.00022, +0.00100]. It may be real information. It may be an artefact of how that one
model family estimates. **This study cannot tell which, and does not pretend to.**

So the question was frozen rather than argued.
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

![One read is spent, one is collecting, one is sealed until 2029](docs/figures/programme-timeline.svg)

Retrospective work can always be re-run until it agrees with you. The defence against that
is a cohort you are allowed to look at only once, under a protocol written and hashed
before that data existed.

One such read is spent. Phase 8A opened on 2026-08-30 and returned `MIXED_EXPLORATORY`:
the state layer was positive in all four cells with descriptive Holm p below 0.05 in
three, while the flow layer crossed zero in all four and cleared Holm in none. An audit
reproduced the registered inference exactly and found **no aggregation change**. The read
is descriptive, **not confirmatory**, and cannot promote anything. Full result in the
[Phase 8A addendum](reports/phase8a_exploratory_bridge_addendum_v10.md).

One cohort is still collecting, and one is sealed until 2029.

---

## What was compared

![Three nested information sets on one shared row mask](docs/figures/information-sets.svg)

Three models see three progressively larger pictures of the same moment, scored on
identical rows. Because the sets nest and share one row mask, the difference between two
rungs is attributable to exactly one layer of information and nothing else.

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

The current bundle stops at the third gate. Its point-in-time inputs have not received a
successor method freeze, so every number it produced stays historical. That is the state
this repository publishes, stated in full under
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
$env:MDS650_PANEL_GUARD_MAY_SKIP = "1"; uv run pytest
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

**No result is currently eligible as the project headline.** The corrected-protocol bundle
is `rp2-v3-20260827-remediation3`, scientific hash
`386610a4908d601c1ad09688d8371cfa3fdd70e4e7ddf50c416e8d3b0907cb47`, status
`REBUILD_COMPLETE_PIT_V22_BLOCKED`. The divergence between the two inference stages is
repaired and the full rebuild passes, but `PIT_V22_RECONCILIATION_BLOCKED` remains.

The authority is [`data/CANONICAL_STATE.json`](data/CANONICAL_STATE.json): one run
manifest, one hash, one eligibility state and its blocking reasons. If any document
disagrees with it, the canonical state wins.

Superseded measurements stay available for audit, never as current findings:

- [`docs/rp2_v3/SUPERSEDED_RESULTS.md`](docs/rp2_v3/SUPERSEDED_RESULTS.md) — what was
  retired, and why.
- [`docs/rp2_v3/VERDICT.md`](docs/rp2_v3/VERDICT.md) — the narrative for the
  corrected-protocol bundle, marked `HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM`.
- [`docs/pit_v22_claims_and_limitations.md`](docs/pit_v22_claims_and_limitations.md) — the
  point-in-time evidence boundary and the gate it still needs.

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
