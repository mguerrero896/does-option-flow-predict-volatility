# MDS650 repository architecture

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

## Scientific flow

1. Provider inputs are normalized with source and timing provenance.
2. Five-minute forecast origins are mapped to a 30-minute realized-variance target.
3. B0, B1 and B2 are nested information sets evaluated on a common eligible mask.
4. Model families are trained under the recorded session-aware split.
5. Forecasts, losses, selected rounds and inference inputs are persisted in the run bundle.
6. A scorecard evaluates contracts and eligibility.
7. The canonical-state producer selects one run and publishes its blocking reasons.

Development measurements remain historical when a later gate invalidates their eligibility.
Phase 8 and Phase 9 have separate prospective collection and read contracts.

## Safety invariants

- `capital_go=false`; the repository performs research, not order execution.
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
