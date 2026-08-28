-- Applied to Supabase as migration 20260827073145 retire_ineligible_current_rp2_results.
-- Remote statements MD5: 50620b2b0317b0de71e50ee2809c44ec.
-- Do not edit; corrections are new migrations.
-- ---- verbatim applied SQL follows ----
-- The canonical repository state has no current eligible RP2 result. Preserve every
-- historical row, empty all four current views, and close the live publication RPC until
-- a future owner-reviewed migration records a newly eligible result.

revoke execute on function public.publish_rp2_v3(jsonb) from service_role;

do $$
declare
  current_rows integer;
begin
  perform pg_advisory_xact_lock(hashtext('rp2:current-result-retirement'));

  select
    (select count(*) from public.rp2_block_results where is_current)
    + (select count(*) from public.rp2_contrast_results where is_current)
    + (select count(*) from public.rp2_extension_results where is_current)
    + (select count(*) from public.rp2_power_results where is_current)
  into current_rows;

  if current_rows = 0 then
    return;
  end if;

  if current_rows <> 40
     or (select count(*) from public.rp2_block_results where is_current) <> 9
     or (select count(*) from public.rp2_contrast_results where is_current) <> 24
     or (select count(*) from public.rp2_extension_results where is_current) <> 7
     or (select count(*) from public.rp2_power_results where is_current) <> 0
     or exists (
       select 1 from public.rp2_block_results
       where is_current and run_id not in (
         'rp2-legacy-unrecorded', 'rp2-v3-20260822-114000', 'rp2v2-remediation'
       ))
     or exists (
       select 1 from public.rp2_contrast_results
       where is_current and run_id <> 'rp2-v3-20260822-114000'
     )
     or exists (
       select 1 from public.rp2_extension_results
       where is_current and run_id <> 'rp2-legacy-unrecorded'
     ) then
    raise exception 'RP2_CURRENT_RETIREMENT_PRECONDITION_FAILED:%', current_rows;
  end if;

  update public.rp2_block_results set is_current = false where is_current;
  update public.rp2_contrast_results set is_current = false where is_current;
  update public.rp2_extension_results set is_current = false where is_current;
  update public.rp2_power_results set is_current = false where is_current;

  if exists (select 1 from public.rp2_block_results where is_current)
     or exists (select 1 from public.rp2_contrast_results where is_current)
     or exists (select 1 from public.rp2_extension_results where is_current)
     or exists (select 1 from public.rp2_power_results where is_current) then
    raise exception 'RP2_CURRENT_RETIREMENT_POSTCONDITION_FAILED';
  end if;
end
$$;
