# Supabase advisor register — measured 2026-08-27

Live advisor output for project `eqpyjikcewqaegnbaemf`, classified formally.
Nothing here is dismissed blindly; every class carries a disposition and, where
action is deferred, the reason and the trigger that un-defers it.

## Security

| Finding | Count | Disposition |
|---|---|---|
| `security_definer_view` on `api.current_rp2_*` | 0 | **RESOLVED** by `20260826020000`: all four are `security_invoker`. Migration `20260826210228` subsequently closes their base-table grants/policies and the view grants, avoiding a public side door. |
| `rls_enabled_no_policy` (INFO) | Re-measured after each migration | **Deliberate** for closed tables: policy-free RLS plus revoked grants is the closure mechanism. `scripts/verify_access_posture.py` accepts only an empty RLS result or explicit SQLSTATE 42501 denial. |
| `supabase_admin` default ACL grants | Platform-managed residual | The repository migration role is `postgres` and cannot alter `supabase_admin` defaults (`permission denied to change default privileges`). Live inspection on 2026-08-27 found zero `public` objects owned by `supabase_admin`; migration `20260826210228` hardens the `postgres` defaults that govern repository DDL. Re-audit ownership after platform-created schema changes. |

## Performance

| Finding | Count | Disposition |
|---|---|---|
| `unindexed_foreign_keys` on `run_id` / `supersedes_run_id` (7 tables, 8 FKs) | 8 | **RESOLVED 2026-08-25**: applied as migration `20260825192000_fk_covering_indexes` on the owner's explicit authorization, measured 0/8 indexes before and 8/8 after, registered in `supabase_migrations.schema_migrations` and versioned in Git with its md5 in the tripwire. Additive and idempotent; rollback is one `drop index if exists` per line. |
| `no_primary_key` (6 dataset tables plus 6 run-scoped staging tables) | 12 | **Deferred**: adding PKs to multi-million-row loaded tables requires a duplicate audit and a key contract. The loader is now run-scoped and hash/count verified; that does not prove row uniqueness. Do not add keys by inference. |
| `unused_index` | 9 | **Keep**: "never used" reflects near-zero query load, not uselessness. Several indexes cover foreign keys. Re-evaluate only with representative query metrics. |
| `auth_db_connections_absolute` (INFO) | 1 | No Auth usage in this project (service/anon keys only); irrelevant at current instance size. Revisit only if Auth is ever adopted. |

## Standing rule

A future advisor finding lands HERE with a disposition before any DDL answers
it, and any DDL that does answer it is a new dated migration registered in
`tests/contract/test_supabase_migrations_present.py`.
