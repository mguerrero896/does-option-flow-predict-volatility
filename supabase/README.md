# supabase/ — schema history and public v4 results

The 2026-09-09 Sydney refresh adds only three public aggregate tables:
`rp4_v4_primary_statistics` (24 rows), `rp4_v4_coverage` (36), and
`rp4_v4_horizons` (3). Nine aggregate/registry tables are now public. The existing
four curated `api` views and private storage bucket are unchanged.
[Before/after schema and anonymous-read receipt](../artifacts/rp4_public_refresh/supabase_receipt.json).

Migration `20260908153626_rp4_v4_public_aggregate_results` is the twentieth applied
migration. It grants readers SELECT only and enables RLS with `public_read` on each
new table. `uv run python scripts/sync_supabase_catalog.py --rp4-v4 --dry-run`
validates the saved CSVs; removing `--dry-run` publishes only these three sources
with source hashes and complete read-back checks. The private dataset loader is separate.

The earlier migration draft is historical design, partly superseded by applied
migrations. Remaining type/key work is deferred outside this refresh; no signature
is needed to publish the already authorized v4 aggregate tables. Never execute the
mixed draft wholesale.

## Earlier reconciliation (2026-08-28)

`migrations/` holds the migrations Supabase records as applied to project
`eqpyjikcewqaegnbaemf`, retrieved VERBATIM from
`supabase_migrations.schema_migrations` (each file carries the reconstruction
header). This closes the audit finding that the remote schema could not be
rebuilt from git: `supabase db reset` against these files reproduces the applied
DDL history in order.

At that reconciliation the directory contained all 19 live migrations through
`20260828020327_close_service_role_sensitive_mutation_paths`. The corresponding read-only
live audit is `artifacts/supabase_schema_audit_20260828.json`: the four versioned result
tables and four current views contain zero current rows, `publish_rp2_v3(jsonb)` is not
executable by `anon`, `authenticated` or `service_role`, and `service_role` cannot mutate
the four retired result tables. The six hash-verified dataset tables retain the privileges
required by their atomic loader.

`verification/default_acl_posture.sql` is the read-only catalog query for repeating the
owner and default-privilege audit. It reads metadata only and does not inspect scientific
rows.

What the reconciliation established, for the record:

- The one migration previously versioned here (`20260820170000_...`, 36.9 KB)
  NEVER matched what was applied (8.1 KB, stamped `20260821034446`). It is
  preserved as design history in `drafts/`, clearly marked.
- The four `api.current_rp2_*` views were converted to `security_invoker` by
  `20260826020000`, but that migration also exposed their four base tables.
  `20260826210228` closes both routes; only the six aggregate tables and four curated
  aggregate views listed in `data/access_posture.json` remain public.
- `migrations_pending/rp2_block14_pending.sql` remains pending AND is known to be
  PARTIALLY superseded (three of its policies already exist remotely, created by
  `20260818232500`). Do not run it as written: it must be split into exact
  chronological migrations first (audit decision, 2026-08-25).
