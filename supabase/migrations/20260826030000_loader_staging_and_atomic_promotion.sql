-- Applied 2026-08-26T03:00Z and registered in supabase_migrations.schema_migrations.
-- Ends the loader's audit hold by fixing its cause instead of gating it: a control
-- table keyed by the source SHA-256 (a row count cannot tell changed content from
-- same-sized content), one staging table per dataset, and promote_dataset(), which
-- does the delete, the insert and the digest record in a SINGLE transaction and
-- refuses to promote empty staging. Rollback: drop the function and the __staging
-- tables; the live tables are untouched by this migration.
-- Do not edit; corrections are new migrations.
-- ---- verbatim applied SQL follows ----
create table if not exists public.dataset_loads (
  table_name   text primary key,
  source_path  text not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  row_count    bigint not null check (row_count >= 0),
  loaded_at    timestamptz not null default now()
);
alter table public.dataset_loads enable row level security;
create or replace function public.promote_dataset(
  p_table text, p_source_path text, p_sha256 text
) returns bigint language plpgsql security definer set search_path = public, pg_temp as $fn$
declare v_rows bigint;
begin
  if p_table !~ '^[a-z][a-z0-9_]{2,62}$' then raise exception 'PROMOTE_REJECTED_TABLE_NAME: %', p_table; end if;
  execute format('select count(*) from %I', p_table || '__staging') into v_rows;
  if v_rows = 0 then raise exception 'PROMOTE_REFUSED_EMPTY_STAGING: %', p_table; end if;
  execute format('delete from %I', p_table);
  execute format('insert into %I select * from %I', p_table, p_table || '__staging');
  insert into public.dataset_loads(table_name, source_path, source_sha256, row_count)
    values (p_table, p_source_path, p_sha256, v_rows)
    on conflict (table_name) do update set source_path = excluded.source_path,
      source_sha256 = excluded.source_sha256, row_count = excluded.row_count, loaded_at = now();
  execute format('truncate %I', p_table || '__staging');
  return v_rows;
end;
$fn$;
revoke all on function public.promote_dataset(text, text, text) from public, anon, authenticated;
create table if not exists public.dev_training_all_origins__staging (like public.dev_training_all_origins including defaults);
create table if not exists public.dev_training_common__staging (like public.dev_training_common including defaults);
create table if not exists public.c1_development_forecasts__staging (like public.c1_development_forecasts including defaults);
create table if not exists public.c5_frozen_evaluation_forecasts__staging (like public.c5_frozen_evaluation_forecasts including defaults);
create table if not exists public.b1v3_features__staging (like public.b1v3_features including defaults);
create table if not exists public.b2_mechanism_forecasts__staging (like public.b2_mechanism_forecasts including defaults);
