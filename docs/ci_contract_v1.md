# CI contract (v1, 2026-08-18 — reviewer correction)

Two verification tiers, each with an explicit claim and an explicit gap.

## Tier 1 — hermetic, hosted, mandatory (GitHub Actions, every push/PR)

Jobs in `.github/workflows/ci.yml`:

| Job | Contents |
|---|---|
| `quality` | `uv sync --locked`, Ruff, mypy strict |
| `hermetic` | Full pytest suite minus the one licensed-evidence file below — unit tests, property-based tests (hypothesis, `tests/unit/test_property_core.py`), synthetic end-to-end pipeline tests (`tests/e2e/`, fixture-only, never a provider call), schema/contract tests over git-tracked artifacts — with a **coverage gate ≥ 80 % of `src/mds650`** (measured 81.03 % at introduction) |
| `scientific-contracts` | The RP2 scientific-contract tests (`tests/contract/`) under `MDS650_PANEL_GUARD_MAY_SKIP=1`: the tier boundary is declared, so the six per-set panel-coverage assertions that need licensed panels skip HERE by name and run under tier 2 instead (added 2026-08-24) |

Evidence-bound tests self-skip on the runner via `tests/evidence.py`
(`MDS650_EVIDENCE_ROOT` unset → `pytest.skip`), so they count as skipped, never as
green-washed passes.

Excluded from tier 1:

1. `tests/unit/test_independent_replication_panel.py` — hard-requires
   `<DATA_ROOT>/independent_replication_30/...` with no skip guard.

The B2 missingness contract now constructs its predictor fixture under `tmp_path`, and
canonical text producers emit LF on every operating system. Those tests therefore run in
tier 1 instead of borrowing local data or requiring platform-specific ignores.

## Tier 2 — local, licensed evidence (before every publish)

`uv run python scripts/run_local_evidence_gates.py` runs with true exit codes:

1. Ruff + mypy (parity with tier 1),
2. the **full** pytest suite — including the licensed-evidence file above and every
   evidence-root contract against the real local store,
3. SHA-256 verification of all gated files against `data/GATED_DATA_POINTERS.json`
   (provider integration probes stay under the `live` marker and are run only under
   the registered request budgets; canonical reproduction has its own sealed runner in
   `artifacts/canonical_validation_v1/reproduce.ps1`).

Tier 2 is what licenses the publish claim "the complete suite passes against the real
evidence"; tier 1 is what a stranger's PR is judged by.

## Branch protection

`main` on the public mirror requires the `quality`, `hermetic` and
`scientific-contracts` checks (strict, admins included). **Force pushes are
disallowed since the 2026-08-25 hardening** — this deliberately supersedes the
original "allowed by design" stance: the whole-history republish path
(`scripts/publish_mirror.sh`) was already blocked by its ancestry guard pending a
governance decision, so protection now also refuses the force-push it would need.
Republishing the history therefore requires recorded approval and a temporary
protection lift for the duration — an explicit action, never a default.

## Commit signatures — documented limitation

The public mirror's commits are **rewritten** by `git filter-repo` on every publish;
rewriting discards any signature made on the canonical commits, so "Verified" badges
on mirror commits are structurally impossible without re-signing generated history on
each publish (which would churn every hash non-deterministically). Integrity of the
mirror is instead guaranteed by the publish script's dual verification (no gated path
in any published commit; blob-for-blob equality with the canonical history excluding
gated paths) plus the SHA-256 registry. A visible signature can be added by signing
the annotated release tags with an SSH signing key registered in GitHub settings.
