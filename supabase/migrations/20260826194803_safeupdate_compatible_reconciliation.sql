-- Applied to Supabase as migration 20260826194803 safeupdate_compatible_reconciliation.
-- Remote statements MD5: b4bd1196d32c1e5b0065f6d16d8421e4.
-- Do not edit; corrections are new migrations.
-- ---- verbatim applied SQL follows ----
-- PENDING OWNER-APPLIED CORRECTION.
-- The first live catalog sync after 20260826180409 failed closed with SQLSTATE
-- 21000: "DELETE requires a WHERE clause". This project enforces safeupdate, so
-- every intentional full-table replacement must carry an explicit WHERE clause.

-- The legacy RPC accepts any syntactically valid public table name. The loader now
-- uses the allowlisted, run-scoped v2 function, so remove the legacy service path.
revoke execute on function public.promote_dataset(text, text, text) from service_role;

create or replace function public.promote_dataset_v2(
  p_table text, p_source_path text, p_sha256 text, p_load_id uuid
) returns bigint language plpgsql security definer set search_path = public, pg_temp as $fn$
declare v_rows bigint; v_columns text;
begin
  if p_table not in ('dev_training_all_origins', 'dev_training_common',
                     'c1_development_forecasts', 'c5_frozen_evaluation_forecasts',
                     'b1v3_features', 'b2_mechanism_forecasts') then
    raise exception 'PROMOTE_REJECTED_TABLE: %', p_table;
  end if;
  if p_sha256 !~ '^[0-9a-f]{64}$' then raise exception 'PROMOTE_REJECTED_SHA256'; end if;
  perform pg_advisory_xact_lock(hashtextextended('dataset-promotion:' || p_table, 0));
  execute format('select count(*) from %I where load_id = $1', p_table || '__staging')
    into v_rows using p_load_id;
  if v_rows = 0 then raise exception 'PROMOTE_REFUSED_EMPTY_STAGING: %', p_table; end if;
  select string_agg(quote_ident(attname), ', ' order by attnum) into v_columns
  from pg_attribute
  where attrelid = format('public.%I', p_table)::regclass and attnum > 0 and not attisdropped;
  execute format('delete from %I where true', p_table);
  execute format('insert into %I (%s) select %s from %I where load_id = $1',
                 p_table, v_columns, v_columns, p_table || '__staging') using p_load_id;
  insert into public.dataset_loads(table_name, source_path, source_sha256, row_count)
    values (p_table, p_source_path, p_sha256, v_rows)
    on conflict (table_name) do update set source_path = excluded.source_path,
      source_sha256 = excluded.source_sha256, row_count = excluded.row_count, loaded_at = now();
  execute format('delete from %I where load_id = $1', p_table || '__staging') using p_load_id;
  return v_rows;
end;
$fn$;
revoke all on function public.promote_dataset_v2(text, text, text, uuid) from public, anon, authenticated;
grant execute on function public.promote_dataset_v2(text, text, text, uuid) to service_role;

create or replace function public.reconcile_research_catalog(p_payload jsonb)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $fn$
declare v_campaigns bigint; v_contrasts bigint; v_cells bigint; v_gated bigint;
begin
  if not (jsonb_typeof(p_payload->'campaigns') = 'array'
          and jsonb_typeof(p_payload->'contrasts') = 'array'
          and jsonb_typeof(p_payload->'cells') = 'array'
          and jsonb_typeof(p_payload->'gated') = 'array') then
    raise exception 'CATALOG_PAYLOAD_INVALID';
  end if;
  perform pg_advisory_xact_lock(hashtextextended('research-catalog-reconciliation', 0));
  insert into public.campaigns(campaign_id, sessions, row_count, input_sha256, note)
  select campaign_id, sessions, row_count, input_sha256, note
  from jsonb_to_recordset(p_payload->'campaigns') as r(campaign_id text, sessions integer,
    row_count bigint, input_sha256 text, note text)
  on conflict (campaign_id) do update set sessions = excluded.sessions, row_count = excluded.row_count,
    input_sha256 = excluded.input_sha256, note = excluded.note;
  delete from public.contrast_results where true;
  insert into public.contrast_results(campaign_id, block_id, model_role, contrast, p_wild_status,
    estimate, cluster_t, p_cluster, p_newey_west, p_wild, rho1, ljung_box_p)
  select campaign_id, block_id, model_role, contrast, p_wild_status, estimate, cluster_t,
    p_cluster, p_newey_west, p_wild, rho1, ljung_box_p
  from jsonb_to_recordset(p_payload->'contrasts') as r(campaign_id text, block_id text,
    model_role text, contrast text, p_wild_status text, estimate double precision,
    cluster_t double precision, p_cluster double precision, p_newey_west double precision,
    p_wild double precision, rho1 double precision, ljung_box_p double precision);
  delete from public.campaigns c where not exists (
    select 1 from jsonb_to_recordset(p_payload->'campaigns') as r(campaign_id text) where r.campaign_id = c.campaign_id
  );
  delete from public.mcs_cells where true;
  insert into public.mcs_cells(campaign_id, block_id, block_length, cell, mcs_p, survivor)
  select campaign_id, block_id, block_length, cell, mcs_p, survivor
  from jsonb_to_recordset(p_payload->'cells') as r(campaign_id text, block_id text,
    block_length integer, cell text, mcs_p double precision, survivor boolean);
  insert into public.gated_files(path, sha256, bytes, bucket_object)
  select path, sha256, bytes, bucket_object
  from jsonb_to_recordset(p_payload->'gated') as r(path text, sha256 text, bytes bigint, bucket_object text)
  on conflict (path) do update set sha256 = excluded.sha256, bytes = excluded.bytes,
    bucket_object = excluded.bucket_object;
  if exists (
    select 1 from public.gated_files g where not exists (
      select 1 from jsonb_to_recordset(p_payload->'gated') as r(path text) where r.path = g.path
    ) and exists (select 1 from public.access_grants a where a.bucket_object = g.bucket_object)
  ) then raise exception 'CATALOG_STALE_GATED_FILE_HAS_ACCESS_GRANTS'; end if;
  delete from public.gated_files g where not exists (
    select 1 from jsonb_to_recordset(p_payload->'gated') as r(path text) where r.path = g.path
  );
  select count(*) into v_campaigns from public.campaigns;
  select count(*) into v_contrasts from public.contrast_results;
  select count(*) into v_cells from public.mcs_cells;
  select count(*) into v_gated from public.gated_files;
  return jsonb_build_object('campaigns', v_campaigns, 'contrasts', v_contrasts,
                            'cells', v_cells, 'gated', v_gated);
end;
$fn$;
revoke all on function public.reconcile_research_catalog(jsonb) from public, anon, authenticated;
grant execute on function public.reconcile_research_catalog(jsonb) to service_role;
