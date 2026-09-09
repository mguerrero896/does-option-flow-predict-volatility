# Research repository architecture

**Status: CURRENT.** Read the [current scientific evidence](CURRENT.md) for the
result and the RP4 implementation boundary below for its recorded code path.

This document describes the maintained repository structure. Scientific eligibility is not
defined here: `data/CANONICAL_STATE.json` is the machine-readable authority and `STATUS.md`
is its generated human projection.

## System shape

```text
provider or frozen input
        |
        v
scripts/ entrypoint -----> src/mds650/ reusable contracts
        |                          |
        +------------+-------------+
                     v
       immutable or deterministic artifact
                     |
          +----------+-----------+
          |                      |
          v                      v
  frozen/pointer registry   scorecard and manifest
          |                      |
          +----------+-----------+
                     v
          data/CANONICAL_STATE.json
                     |
          +----------+-----------+
          v                      v
       STATUS.md             public reports
```

Scripts orchestrate; the package implements reusable behavior; artifacts carry evidence;
the canonical state selects what is current. A document or database row cannot promote a
result independently of that chain.

## Components

| Component | Role | Boundary |
| --- | --- | --- |
| `src/mds650/providers/` | Provider clients and payload parsing | Provider timestamps establish only the semantics documented by the PIT contracts. |
| `src/mds650/rp2/` | RP2 panel, model, inference and run-manifest contracts | Shared producers must receive real session labels and preserve common masks. |
| `src/mds650/config.py` | Validated environment and data-root resolution | Provides production, sandbox and RP2 resolvers; maintained entrypoints resolve them before I/O and fail closed when required configuration is absent. |
| `src/mds650/sealed.py` | Sealed-path access guard | A method freeze or executable does not grant outcome access. |
| `scripts/run_rp2_v3_pipeline.py` | Ordered RP2-v3 rebuild coordinator | One run id, stable inputs, fixed step order and no sealed cohorts. |
| `scripts/generate_canonical_state.py` | Current-state producer | Reads an allowlist of authoritative sources and generates both canonical outputs. |
| `scripts/run_local_evidence_gates.py` | Licensed Tier 2 validation | Must not be represented as hosted/public CI. |
| `scripts/verify_scheduled_tasks.py` | Windows task liveness and target validation | Checks required tasks, action targets, working directories, restart policy and future triggers. |
| `scripts/load_supabase_datasets.py` | Six-dataset loader | Run-scoped staging and server-side promotion prevent partial or interleaved snapshots. |
| `scripts/sync_supabase_catalog.py` | Aggregate catalog reconciliation | Repository artifacts remain authoritative; reconciliation is exact and atomic. |
| `supabase/migrations/` | Database schema and privilege history | Ordered SQL is the reproducible database contract. |

The complete lifecycle and purpose of every top-level entrypoint is maintained in
[`scripts/README.md`](../scripts/README.md).

## Evidence planes

### Hermetic public plane

Contains tracked code, fixtures, schemas, aggregate artifacts and hashes. Hosted CI can
verify deterministic behavior and documentation contracts without provider credentials.

### Licensed local plane

Contains provider-derived granular rows outside public Git. Pointer manifests bind those
bytes to the public repository without redistributing them. Tier 2 checks require the
configured local evidence root.

### Live operational plane

Contains provider calls, Windows scheduled tasks and Supabase interactions. Each live
entrypoint is bounded independently. A live health check verifies wiring or access posture;
it does not authorize a scientific read.

Four scheduled-task targets are intentionally local-only and absent from the public mirror:
`sync_project_knowledge.ps1`, `phase8_run_daily.ps1`, `phase8_watch.ps1` and
`phase8_health_watch.ps1`. The verifier requires the active knowledge target to resolve.
The Phase 8 targets belong to retired tasks: their continued disabled state is the safety
invariant, so their private files need not remain online.

## Historical RP2 scientific flow

1. Provider inputs are normalized with source and timing provenance.
2. Five-minute forecast origins are mapped to a 30-minute realized-variance target.
3. B0, B1 and B2 are nested information sets evaluated on a common eligible mask.
4. Model families are trained under the recorded session-aware split.
5. Forecasts, losses, selected rounds and inference inputs are persisted in the run bundle.
6. A scorecard evaluates contracts and eligibility.
7. The canonical-state producer selects one run and publishes its blocking reasons.

Development measurements remain historical when a later gate invalidates their eligibility.
Phase 8 and Phase 9 have separate collection and read contracts; this historical
flow is not the current RP4 design. RP4 v4 uses RV15 primary and RV5 secondary
targets, as specified in [current evidence](CURRENT.md).

## RP4 implementation and execution boundary

The current scientific result is RP4 v4, but there is no `src/mds650/rp4` package. Its recorded evaluation implementation lives in versioned snapshots under `artifacts/`, with explicit imports from earlier snapshots and shared `src/mds650` modules. The general scripts-to-package diagram above does not imply a maintained RP4 fitting entrypoint under `scripts/`.

| Stage | Recorded implementation and entrypoint | Actual dependencies |
| --- | --- | --- |
| Target construction | [materialize_targets.py](../artifacts/rp4_v4_code/materialize_targets.py): `main()` calls `run()` | `panel_masks` from [evaluate_v2.py](../artifacts/rp4_v2_code/evaluate_v2.py); `BAR_SOURCES` and `SessionGrid` from [bars.py](../src/mds650/rp2/bars.py); `forward_measures` and `log_returns` from [realized.py](../src/mds650/rp2/realized.py). |
| Window orchestration | [execute.py](../artifacts/rp4_v4_code/execute.py): `main()` and `run_window()` | v4 evaluator helpers, `select_bar_pins` from the target materializer, and `window_lock` from the [v2 executor](../artifacts/rp4_v2_code/execute.py). |
| Chronological fitting | [evaluate_v4.py](../artifacts/rp4_v4_code/evaluate_v4.py): `main()` calls `run()` | Earlier evaluator modules; `fit_ridge` from [v3 models](../artifacts/rp4_v3_code/models.py); `fit_lightgbm` from [v2 models](../artifacts/rp4_v2_code/models.py). |
| Saved inference | [aggregate_v4.py](../artifacts/rp4_v4_code/aggregate_v4.py): `aggregate_records()` | [v3 aggregation](../artifacts/rp4_v3_code/aggregate_v3.py), [v3 inference](../artifacts/rp4_v3_code/inference.py), and `holm_adjust` from [metrics.py](../src/mds650/metrics.py). This module is an imported aggregation function, not a separate CLI. |
| Historical reporting | [report_v4_checked.py](../artifacts/rp4_v4_code/report_v4_checked.py): `run()` | Saved summaries, losses, diagnostics and receipts. Its historical reporting receipt records zero additional model fits and zero new inference. The public producer's bytes differ from the original execution hash; see the [evidence map](EVIDENCE_MAP.md). |
| Maintained public state | [generate_canonical_state.py](../scripts/generate_canonical_state.py): `build_state()` and `build_current_claims()` | Saved aggregate evidence, including the pinned primary CSV. This is a reporting projection, not the RP4 fitting implementation. |

The shared inference path imports `newey_west_variance` and `session_block_draws` from [RP2 inference](../src/mds650/rp2/inference.py). Both versioned model modules import `qlike_losses` from [metrics.py](../src/mds650/metrics.py) and `lightgbm_objective` from [qlike_objective.py](../src/mds650/rp2/qlike_objective.py). Reuse of the RP2 namespace identifies implementation ownership; it does not substitute RP2 results for RP4 evidence.

### Identity and portability

The evaluator's `evaluation_code_hashes()` records the explicit `SOURCE_PATHS` inherited from the earlier evaluator and extended for v4. The executor writes that mapping as `evaluation_code_sha256`. The target materializer separately pins shared bar/realized-variance sources and checks the loaded `forward_measures` implementation path. The [report manifest](../artifacts/rp4_v4_b4/report_manifest.json) records shared metrics, inference and objective inputs alongside snapshot hashes.

Those pins matter when maintained shared code changes: a later package version cannot silently stand in for the code used to produce the historical result. The [evidence map](EVIDENCE_MAP.md) distinguishes calculated public-file hashes from historical recorded hashes; matching one module does not establish identity of the entire execution environment.

The snapshot files retain execution-context assumptions, including private-input references. Their presence is not evidence that a clean public clone can rebuild licensed panels or rerun the scientific evaluation. The [reproduction guide](reproduce.md) describes public checks; the [historical operating guide](rp4/OPERATING_GUIDE.md) records the licensed execution boundary. A visible `main()` function is not authorization to rerun a registered evaluation.

### Maintenance decision

No code relocation is required to inspect or verify the published result. Moving snapshot implementations into a new package would change paths that are part of their recorded identity and introduce another implementation surface without demonstrating additional reproducibility. Keep the snapshots and shared imports intact for this release. A maintained RP4 execution package would be justified by a separately authorized execution requirement, with explicit provenance mapping, licensed-input resolution and parity checks against the recorded implementation before any new scientific read.

## Safety invariants

- Research only. Not investment advice.
- Licensed granular data never enters public Git history.
- Sealed-cohort counters cannot change during method development, documentation or health
  checks.
- Generated artifacts are changed through their producer, not by hand.
- Database mutations are migration- or transaction-bound and verified after application.
- Public publication starts from the sanitized lineage and must pass the ancestry guard.
- Historical files remain available for audit but cannot override canonical eligibility.

## Notebook and estimand boundary

Colab is orchestration and
presentation only. It imports the maintained package and may render public artifacts; it
does not duplicate acquisition, feature building, fitting or inference logic. Historical
backfill remains explicitly `authorized_for_backfill=false`.

The ordinary-option versus trade-augmented comparison keeps the registered orientation
`Delta_Q = QLIKE(B1) - QLIKE(B2)`: positive values favour the augmented information set.

## Maintainer navigation

- [`docs/DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) — onboarding and change workflow.
- [`docs/INDEX.md`](INDEX.md) — current research documentation and historical boundaries.
- [`reports/INDEX.md`](../reports/INDEX.md) — current and historical reports.
- [`data/DATA_ACCESS.md`](../data/DATA_ACCESS.md) — licensed-data custody.
- [`supabase/README.md`](../supabase/README.md) — database layout and migration discipline.
