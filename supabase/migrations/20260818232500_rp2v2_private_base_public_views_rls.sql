-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
-- RP2-v2 hardening, part 2: private base tables, a whitelisted public read model, RLS.
--
-- Base tables stay policy-free, so only the service role reaches them. The public surface
-- is a set of security_invoker views over the AGGREGATE tables only. No origin-level panel
-- is exposed: those are derived works of licensed provider data.

create schema if not exists api;
comment on schema api is
  'Public read model. Only aggregate research results appear here; licensed-derived origin-level panels never do.';

create or replace view api.research_blocks
with (security_invoker = true) as
select block_id, title, status, advance_rule, verdict, document
from public.rp2_blocks;

create or replace view api.research_extensions
with (security_invoker = true) as
select extension_id, question, result, evidence, document
from public.rp2_extensions;

create or replace view api.prospective_power
with (security_invoker = true) as
select contrast, role, detail, sessions_for_80pct,
       power_n30, power_n60, power_n120, method, note
from public.rp2_power
where method <> 'ex_post_max_t_INVALIDATED';

comment on view api.prospective_power is
  'Power curves from blocked simulation. Rows produced by the invalidated ex-post max-|t| rescaling are filtered out here rather than deleted from the base table.';

create or replace view api.campaign_contrasts
with (security_invoker = true) as
select c.campaign_id, c.sessions, c.row_count,
       r.block_id, r.model_role, r.contrast,
       r.estimate, r.cluster_t, r.p_cluster, r.p_newey_west, r.p_wild, r.p_wild_status
from public.campaigns c
join public.contrast_results r on r.campaign_id = c.campaign_id;

-- Read policies on the aggregate tables only. gated_files, access_grants and every
-- origin-level panel are deliberately left policy-free: service role only.
drop policy if exists rp2_blocks_public_read on public.rp2_blocks;
create policy rp2_blocks_public_read on public.rp2_blocks
  for select to anon, authenticated using (true);

drop policy if exists rp2_extensions_public_read on public.rp2_extensions;
create policy rp2_extensions_public_read on public.rp2_extensions
  for select to anon, authenticated using (true);

drop policy if exists rp2_power_public_read on public.rp2_power;
create policy rp2_power_public_read on public.rp2_power
  for select to anon, authenticated using (true);

drop policy if exists campaigns_public_read on public.campaigns;
create policy campaigns_public_read on public.campaigns
  for select to anon, authenticated using (true);

drop policy if exists contrast_results_public_read on public.contrast_results;
create policy contrast_results_public_read on public.contrast_results
  for select to anon, authenticated using (true);

drop policy if exists mcs_cells_public_read on public.mcs_cells;
create policy mcs_cells_public_read on public.mcs_cells
  for select to anon, authenticated using (true);

alter table public.ingestion_runs   enable row level security;
alter table public.ingestion_inputs enable row level security;

grant usage on schema api to anon, authenticated;
grant select on api.research_blocks, api.research_extensions,
                api.prospective_power, api.campaign_contrasts to anon, authenticated;
