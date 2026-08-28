-- Applied 2026-08-25T19:20Z to project eqpyjikcewqaegnbaemf, then registered in
-- supabase_migrations.schema_migrations and versioned here. Closes the eight
-- unindexed foreign keys the advisor reports (supabase/ADVISOR_REGISTER.md).
-- Additive and idempotent; rollback is `drop index if exists <name>` per line.
-- Do not edit; corrections are new migrations.
-- ---- verbatim applied SQL follows ----
create index if not exists rp2_block_results_run_id_idx on public.rp2_block_results (run_id);
create index if not exists rp2_block_results_supersedes_run_id_idx on public.rp2_block_results (supersedes_run_id);
create index if not exists rp2_blocks_run_id_idx on public.rp2_blocks (run_id);
create index if not exists rp2_extension_results_run_id_idx on public.rp2_extension_results (run_id);
create index if not exists rp2_extension_results_supersedes_run_id_idx on public.rp2_extension_results (supersedes_run_id);
create index if not exists rp2_extensions_run_id_idx on public.rp2_extensions (run_id);
create index if not exists rp2_power_run_id_idx on public.rp2_power (run_id);
create index if not exists rp2_power_results_run_id_idx on public.rp2_power_results (run_id);
