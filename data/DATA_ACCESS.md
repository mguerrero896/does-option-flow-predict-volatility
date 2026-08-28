# Gated research data — access policy

## Licence scope

The repository's MIT licence covers its authored software and documentation. It
does not cover commercially licensed market data. Provider data remains governed
by the applicable provider terms and is not redistributed here.

The granular derived datasets of this project (15 files: 14 parquets plus one
quote-level diagnostic CSV, ~135 MB — per-origin
feature panels, row-level frozen forecasts, and quote-derived IV attempts) are built
from commercially licensed market-data feeds (FMP, Unusual Whales, Massive) and
**cannot be redistributed publicly** under the provider agreements. They are therefore
not in this repository. This is the project's registered *controlled auditability*
model, implemented literally.

## What IS public

Everything else: all source code, all tests, every methodology document, every
preregistration, and every **aggregate** result (QLIKE deltas, confidence intervals,
p-values, stability tables) in the `artifacts/**/results.json` files.

## How to verify integrity without the data

Every gated file's SHA-256 and byte size are committed in
[`GATED_DATA_POINTERS.json`](GATED_DATA_POINTERS.json). Any result JSON that consumed
a gated file records the same hash in its `inputs` block — the chain of custody is
fully checkable from public material alone.

## How to request the data (reviewers, examiners, replicators)

1. Open a GitHub issue on this repository titled `Data access request`, stating your
   affiliation and purpose, or contact the author directly.
2. The author verifies the purpose is research/review (not redistribution) and issues
   **time-limited signed URLs** for the requested files from private storage.
3. Verify each downloaded file against its SHA-256 in `GATED_DATA_POINTERS.json`, then
   run `scripts/fetch_gated_data.py --manifest <file-with-signed-urls>` (or download
   manually) and place files at their recorded `path`.
4. By requesting access you agree to use the data solely for verification/research and
   not to redistribute it.

Raw provider payloads (hundreds of GB) are never shared; full reproduction from
scratch requires live provider entitlements, as documented in the README.

## Research catalog database (Supabase Postgres, 2026-08-18)

Beyond Storage, the project's Pro Supabase instance (project `eqpyjikcewqaegnbaemf`)
now hosts a queryable research catalog — **aggregates and registry only, never
licensed provider values**:

| Table | Content | Source of truth in repo |
|---|---|---|
| `campaigns` | Frozen campaigns C1–C6 with input SHA-256 | `artifacts/gate1_inference/results.json` |
| `contrast_results` | Studentized statistics per contrast (estimate, cluster-t, Newey-West, wild bootstrap, ρ₁, Ljung-Box) | same |
| `mcs_cells` | Model Confidence Set membership per campaign × block length L | `artifacts/mcs_block_sensitivity/results.json` |
| `gated_files` | Registry of the 15 gated files (path, SHA-256, bytes, bucket object) | `data/GATED_DATA_POINTERS.json` |
| `access_grants` | Log of signed-URL grants (per-request discipline) | — (operational log) |

Row Level Security is enabled on every table. **Anonymous keys can read some of this
schema, and it is deliberate which parts.** Measured against the live REST endpoint with
the anonymous key:

- **Closed.** The six licensed-derived dataset tables below, plus `gated_files`,
  `access_grants` and the ingestion logs, return no rows. They carry zero policies, so
  RLS denies every row, and `anon` and `authenticated` hold no grant of any kind on the
  six licensed tables — a read is refused at the privilege level, before RLS is reached.
- **Open by design.** Six aggregate and registry tables (`campaigns`,
  `contrast_results`, `mcs_cells`, `rp2_blocks`, `rp2_extensions`, `rp2_power`) carry a
  permissive `*_public_read` policy, and four curated `api.*` views are readable through
  the `Accept-Profile: api` header. These publish the same aggregates the repository
  already publishes.
- **Closed versioned results.** The four `rp2_*_results` base tables and their four
  `api.current_rp2_*` convenience views are denied to anonymous and authenticated roles.
  Migration `20260827073145` also revoked the atomic publication RPC from `service_role`
  and retired every current row. Migration `20260828020327` then revoked direct
  service-role mutation privileges on those four retired tables while preserving the six
  dataset tables required by the hash-verified atomic loader.
- **No writes.** Neither role holds INSERT, UPDATE, DELETE or TRUNCATE anywhere in
  `public`. Every `api.*` view runs as `security_invoker`, so a view cannot lend the
  owner's privileges to a caller who lacks them.

*This section was corrected on 2026-08-27 after the live verifier found that migration
`20260826020000` had reopened the four versioned-result base tables. Migration
`20260826210228` closes both those tables and their convenience views while retaining the
six public aggregate tables and four curated aggregate views described above.*

Nothing licensed is exposed, and anonymous/authenticated roles cannot write anywhere. The
posture is recorded machine-readably in `data/access_posture.json`; the latest result and
dataset-registry measurement is `artifacts/supabase_schema_audit_20260828.json`.
`tests/contract/test_access_posture_matches_documentation.py` fails if this page and that
file disagree, and `scripts/verify_access_posture.py` re-measures it against the endpoint.
The lesson is the one this repository already learned elsewhere: a claim about access that
nothing executes is a claim nobody checked.

Sync is one-way, repo → database, idempotent:
`uv run python scripts/sync_supabase_catalog.py` (requires `SUPABASE_SERVICE_KEY`).
The repo artifacts remain the single source of truth; the database is a queryable
view of them, never an editing surface.

### Dataset tables (2026-08-18, second wave)

The gated datasets themselves are additionally loaded as **queryable private tables**
(zero policies, so RLS denies anon and authenticated every row — verified empty through the
REST endpoint, not assumed):
`dev_training_all_origins` (45,440), `dev_training_common` (38,573),
`c1_development_forecasts` (93,288), `c5_frozen_evaluation_forecasts` (356,400),
`b1v3_features` (77,328), `b2_mechanism_forecasts` (1,554,800). Loader:
`uv run python scripts/load_supabase_datasets.py` refuses a partial source set and uses
the parquet SHA-256 as identity. Applied migration
`20260826180409_loader_run_scoped_staging.sql` moved it to run-scoped staging plus an
atomic promotion, and `20260826194803_safeupdate_compatible_reconciliation.sql` made the
deliberate whole-table replacements compatible with the project's safe-update guard. The
repo parquets stay the source of truth; all six exact SHA-256 and row counts are recorded
in `dataset_loads` and match the live tables.
