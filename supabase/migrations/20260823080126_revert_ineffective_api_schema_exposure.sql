-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
-- Reverts expose_api_schema_for_public_aggregate_reads, which did not achieve its effect.
--
-- Setting pgrst.db_schemas on the authenticator role is the self-hosted PostgREST route.
-- On Supabase the exposed-schema list is platform configuration (Project Settings -> API ->
-- Exposed schemas) and overrides the role setting, so the migration left the role carrying a
-- value nothing honours: PostgREST kept answering PGRST106 for the `api` profile, then
-- PGRST205 once its cache reloaded.
--
-- A migration that reads as though it opened public access while public access stayed shut is
-- worse than no migration, so the setting is removed rather than left in place. Exposing the
-- schema is a dashboard toggle, and the owner makes it.
alter role authenticator reset pgrst.db_schemas;
notify pgrst, 'reload config';
