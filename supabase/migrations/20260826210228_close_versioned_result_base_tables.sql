-- Applied to Supabase as migration 20260826210228 close_versioned_result_base_tables.
-- Authorized source: supabase/migrations_pending/20260826205452_close_versioned_result_base_tables.sql.
-- Authorized source SHA-256: 58CFEF9E00B03C6CBDC0ED68F77883B9A117EAA34286F4467D2A749E7837F49B.
-- Remote statements MD5: 1e65e1e1eaf9f73624a3ae8afe6d7ad8.
-- Do not edit; corrections are new migrations.
-- ---- verbatim applied SQL follows ----
-- PENDING OWNER AUTHORIZATION. Close the four versioned-result base tables and their convenience views.
-- Aggregate publication remains available through the six explicitly public
-- registry tables and the four curated api views recorded in access_posture.json.
--
-- The 20260826020000 migration converted the current_rp2_* views to
-- security_invoker but then granted SELECT and is_current policies on their base
-- tables. That exposed additional columns through the public schema and
-- contradicted the measured CLOSED posture. Keep the invoker boundary and close
-- both routes instead of restoring SECURITY DEFINER.

revoke all privileges on table
  public.rp2_block_results,
  public.rp2_contrast_results,
  public.rp2_extension_results,
  public.rp2_power_results
from public, anon, authenticated;

drop policy if exists rp2_block_results_public_read on public.rp2_block_results;
drop policy if exists rp2_contrast_results_public_read on public.rp2_contrast_results;
drop policy if exists rp2_extension_results_public_read on public.rp2_extension_results;
drop policy if exists rp2_power_results_public_read on public.rp2_power_results;

revoke all privileges on table
  api.current_rp2_block_results,
  api.current_rp2_contrasts,
  api.current_rp2_extension_results,
  api.current_rp2_power_results
from public, anon, authenticated;

-- Repository migrations run as postgres. Harden that owner so a future table,
-- sequence or function does not silently restore public access.
alter default privileges for role postgres in schema public
  revoke all on tables from public, anon, authenticated;
alter default privileges for role postgres in schema public
  revoke all on sequences from public, anon, authenticated;
alter default privileges for role postgres in schema public
  revoke execute on functions from public, anon, authenticated;

notify pgrst, 'reload schema';
