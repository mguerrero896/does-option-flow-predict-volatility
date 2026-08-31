# Developer guide

This guide is the maintainer entrypoint for the repository. It explains where authority
lives, how code and evidence flow, and which commands are safe in a public clone. It does
not replace the scientific state in `data/CANONICAL_STATE.json` or the method records in
`docs/methodology_decisions.md`.

## Ten-minute orientation

Read these files in order:

1. [`README.md`](../README.md) — research question, evidence boundary and current result.
2. [`STATUS.md`](../STATUS.md) — generated human projection of the canonical state.
3. [`data/CANONICAL_STATE.json`](../data/CANONICAL_STATE.json) — current run, hashes,
   eligibility and blocking reasons.
4. [`docs/INDEX.md`](INDEX.md) — current methods, historical records and literature.
5. [`scripts/README.md`](../scripts/README.md) — every runnable script and its lifecycle.
6. [`reports/INDEX.md`](../reports/INDEX.md) — current submission source and historical
   report packages.
7. [`docs/rp2_v3/REBUILD_GUIDE.md`](rp2_v3/REBUILD_GUIDE.md) — exact 13-step licensed
   rebuild, storage budget and `--skip-panels`/`--dry-run` semantics.

## Sources of truth

| Question | Authority | Maintenance rule |
| --- | --- | --- |
| What result is current? | `data/CANONICAL_STATE.json` | Regenerate with `scripts/generate_canonical_state.py`; never edit `STATUS.md` manually. |
| Why is a result eligible or blocked? | Canonical state plus its named scorecard and verdict | A narrative cannot override the machine state. |
| Which evidence bytes are frozen? | `data/FROZEN_ARTIFACTS.json` | Change only through the append-only freeze workflow. |
| Which data cannot be distributed? | `data/GATED_DATA_POINTERS.json` and `data/DATA_ACCESS.md` | Keep provider-derived rows out of public Git history. |
| Which protocol governs a future read? | The protocol named under `active_protocols` in canonical state | A frozen or one-shot script is not permission to execute it. |
| Which database schema is reproducible? | `supabase/migrations/` | Never substitute dashboard edits or direct row mutation for a migration. |
| Which report is current? | `reports/INDEX.md` | Regenerate derived formats from the named source document. |

## Repository layers

| Path | Responsibility | What belongs here |
| --- | --- | --- |
| `src/mds650/` | Reusable library | Parsing, validation, features, inference, model and safety contracts. |
| `scripts/` | Explicit entrypoints | Thin orchestration, artifact producers, verification and controlled live operations. |
| `configs/`, `config/` | Frozen or operational configuration | Declared study windows, feature sets and bounded endpoint catalogs. |
| `schemas/`, `specs/` | Machine and research contracts | JSON schemas, acceptance criteria and protocol specifications. |
| `artifacts/` | Public evidence records | Aggregates, manifests, scorecards and sanitized provenance; not an ad hoc output folder. |
| `data/` | Canonical pointers and registries | Current state, frozen registry and licensed-data pointers. |
| `supabase/` | Database reproducibility | Ordered migrations and documented access posture. |
| `tests/` | Executable contracts | Unit, behavioral, documentation, evidence and fixture-only end-to-end checks. |
| `docs/` | Research documentation | Current methods, evidence boundaries and clearly marked historical records. |
| `reports/` | Submission and presentation products | Current source documents and indexed historical packages. |

The repository intentionally keeps historical protocols and artifacts. Moving or deleting
them to make the tree look smaller can break hashes, links and auditability. Organization is
provided by the canonical state and the three indexes, not by rewriting history.

## Execution planes

### Public and hermetic

Safe in a clean public clone; no provider credentials or licensed rows are required:

```powershell
uv sync --locked
uv run ruff check src scripts tests
uv run mypy src scripts
$env:MDS650_PANEL_GUARD_MAY_SKIP = "1"
uv run pytest tests -q --ignore=tests/unit/test_independent_replication_panel.py --cov=src/mds650 --cov-report=term --cov-fail-under=90
```

The skip flag acknowledges that licensed panels are absent. It does not convert the run
into Tier 2 evidence.

### Local licensed-evidence validation

`scripts/run_local_evidence_gates.py` verifies the full local suite, gated hashes and live
access posture. Run it only in the configured evidence environment. A public-clone pass
cannot substitute for this tier.

### Live, frozen or one-shot

Provider acquisition, database mutation and sealed-cohort evaluation have additional
contracts. Before executing one of these scripts:

1. find it in [`scripts/README.md`](../scripts/README.md);
2. read the named protocol and authorization boundary;
3. verify configuration and input hashes;
4. preserve counters, manifests and fail-closed behavior.

The existence of a CLI, token schema or scheduled task is not authorization to read a
sealed outcome or publish a result.

Some operational wrappers are deliberately local-only: `sync_project_knowledge.ps1` and
the three Phase 8 task wrappers are not distributed in the public mirror. The active
knowledge task must resolve its local wrapper. The Phase 8 one-shot read is consumed, so
its three retained tasks must remain disabled and their private targets may be offline.
Publicly maintained entrypoints include the UW latency scripts, Phase 9 scripts and alert
forwarder. Run `uv run python scripts/verify_scheduled_tasks.py` on the configured Windows
host; it enforces both active-task liveness and retired-task shutdown.

### Git and worktree custody

`main` is the only public development line. Do not merge the unrelated archive/recovery or
operational roots into it. The `ops/tasks-checkout` worktree supplies relative entrypoints to
live scheduled tasks and must not be moved or removed while those tasks exist. The locked
Phase 8 recovery worktree preserves the consumed one-shot execution lineage and is not a
source for new development. Before deleting any branch, prove its unique commits are
patch-equivalent or superseded and preserve any untracked files; a `[gone]` upstream alone
is not evidence that a branch is disposable.

The complete licensed rebuild is intentionally outside the public-clone tier. Its ordered
steps, exact invocation, approximately 85 GB storage requirement and resume flags are in
[`docs/rp2_v3/REBUILD_GUIDE.md`](rp2_v3/REBUILD_GUIDE.md).

## Change workflow

### Library or pipeline code

1. Trace the affected entrypoint from `scripts/README.md` into `src/mds650/`.
2. Fix the shared producer or contract rather than patching one generated artifact.
3. Add the smallest behavioral regression that fails on the old behavior.
4. Run the focused test, Ruff and strict mypy.
5. Regenerate only artifacts owned by that producer.
6. Run canonical-state and documentation contracts before proposing publication.

### Documentation

1. Check current eligibility in `data/CANONICAL_STATE.json`.
2. Put current navigation in `docs/INDEX.md`; do not create a competing index.
3. Mark a retained obsolete document `HISTORICAL` or `SUPERSEDED` at its top.
4. Use repository-relative links and run `tests/contract/test_documentation_references.py`.
5. Never edit auto-generated `STATUS.md` directly.

### New or changed script

Every top-level script must have:

- a module docstring stating purpose, boundary and safe invocation;
- `--help` that performs no work;
- configuration through the shared package or explicit arguments, not a personal path;
- a row in `scripts/README.md` with its lifecycle;
- a focused test for any non-trivial branch, parser or safety gate.

Comments should explain **why an invariant exists**, not restate the next line. Examples
include one-read boundaries, equal-session weighting, atomic promotion and the reason a
particular failure must be fail-closed.

### Frozen artifact or canonical-state change

Do not hand-edit a generated result. Locate its producer, rebuild deterministically, update
the appropriate registry through its supported workflow, and verify every downstream hash.
If an authorized source listed by `generate_canonical_state.py` changes, regenerate both
canonical outputs and run their drift tests.

### Supabase

Read [`supabase/README.md`](../supabase/README.md) and
[`data/DATA_ACCESS.md`](../data/DATA_ACCESS.md) first. Compare pending SQL with live
migration history before applying it. Destructive DDL, publication permissions and data
mutation require their own authorization and post-change verification.

GitHub issue [#2](https://github.com/mguerrero896/does-option-flow-predict-volatility/issues/2)
remains the known database follow-up. Its proposed Block 14 migration predates the live
19-migration reconciliation through `20260828020327` and is not an executable plan. Treat
`supabase/migrations_pending/rp2_block14_pending.sql` as partially superseded design
history; compare every proposed statement with fresh live migration history and schema
before requesting separate mutation authority.

## Commenting and naming conventions

- Public functions and modules state their contract in docstrings.
- Inline comments record causality, invariants, provenance or a non-obvious platform limit.
- Generated files identify their producer and say not to edit them manually.
- Version suffixes identify protocol lineage; the unsuffixed or highest-numbered filename is
  not automatically current. Authority comes from the indexes and canonical state.
- New documents use descriptive lowercase names; dates belong in audit snapshots, not in
  every maintained guide.

## Before handing the project to another maintainer

Run and record:

```powershell
uv run ruff check src scripts tests
uv run mypy src scripts
uv run pytest tests/contract/test_documentation_references.py -q
uv run pytest tests/contract/test_canonical_state_current.py -q
```

Then confirm that the worktree is clean, the relevant index names every new file, generated
outputs match their producers, and no claim exceeds the evidence tier that was actually run.
