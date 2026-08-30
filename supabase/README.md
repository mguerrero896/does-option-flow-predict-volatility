# supabase/ — schema history, reconciled 2026-08-28

`migrations/` holds the migrations Supabase records as applied to project
`eqpyjikcewqaegnbaemf`, retrieved VERBATIM from
`supabase_migrations.schema_migrations` (each file carries the reconstruction
header). This closes the audit finding that the remote schema could not be
rebuilt from git: `supabase db reset` against these files reproduces the applied
DDL history in order.

The directory contains all 19 live migrations through
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
