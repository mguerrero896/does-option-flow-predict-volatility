-- Applied 2026-08-26T02:00Z and registered in supabase_migrations.schema_migrations.
-- Least privilege: anon/authenticated held DELETE, INSERT, UPDATE and TRUNCATE on
-- every public table including the six licensed datasets. RLS blocked the writes,
-- but the blast radius of one mistaken policy was the whole schema. Measured after:
-- 0 public DML grants, 0 grants of any kind on the six licensed tables.
-- The four SECURITY DEFINER views become security_invoker, served instead by read
-- policies on their base tables restricted to is_current. Verified as anon: the same
-- rows are still readable (9 blocks, 24 contrasts) by policy rather than by the
-- view owner's privileges, and the licensed tables now refuse at the grant level.
-- Do not edit; corrections are new migrations.
-- ---- verbatim applied SQL follows ----
revoke all on all tables in schema public from anon, authenticated;
alter default privileges in schema public revoke all on tables from anon, authenticated;
drop policy if exists rp2_block_results_public_read on public.rp2_block_results;
create policy rp2_block_results_public_read on public.rp2_block_results
  for select to anon, authenticated using (is_current);
drop policy if exists rp2_contrast_results_public_read on public.rp2_contrast_results;
create policy rp2_contrast_results_public_read on public.rp2_contrast_results
  for select to anon, authenticated using (is_current);
drop policy if exists rp2_extension_results_public_read on public.rp2_extension_results;
create policy rp2_extension_results_public_read on public.rp2_extension_results
  for select to anon, authenticated using (is_current);
drop policy if exists rp2_power_results_public_read on public.rp2_power_results;
create policy rp2_power_results_public_read on public.rp2_power_results
  for select to anon, authenticated using (is_current);
grant select on public.campaigns, public.contrast_results, public.mcs_cells,
                public.rp2_blocks, public.rp2_extensions, public.rp2_power,
                public.rp2_block_results, public.rp2_contrast_results,
                public.rp2_extension_results, public.rp2_power_results
  to anon, authenticated;
alter view api.current_rp2_block_results set (security_invoker = true);
alter view api.current_rp2_contrasts set (security_invoker = true);
alter view api.current_rp2_extension_results set (security_invoker = true);
alter view api.current_rp2_power_results set (security_invoker = true);
grant select on all tables in schema api to anon, authenticated;
