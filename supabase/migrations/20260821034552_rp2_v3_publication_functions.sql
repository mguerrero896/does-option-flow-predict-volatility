-- Reconstructed 2026-08-25 from supabase_migrations.schema_migrations on project
-- eqpyjikcewqaegnbaemf: the EXACT SQL Supabase recorded as applied for this version,
-- verified by md5 against the remote statements. Do not edit; corrections are new
-- migrations. (Recovered a second time on 2026-08-25: PR #43's squash landed empty
-- because these files were never git-added; tests/contract/test_supabase_migrations_present.py
-- now pins presence and body md5 so that cannot silently happen again.)
-- ---- verbatim applied SQL follows ----
create or replace function public.publish_rp2_v3(payload jsonb)
returns jsonb
language plpgsql
security invoker
set search_path = public
as $$
declare
    run jsonb := payload -> 'run';
    published_run_id text := run ->> 'run_id';
    input_rows integer := coalesce(jsonb_array_length(payload -> 'inputs'), 0);
    block_rows integer := coalesce(jsonb_array_length(payload -> 'blocks'), 0);
    contrast_rows integer := coalesce(jsonb_array_length(payload -> 'contrasts'), 0);
    superseded jsonb;
begin
    if published_run_id is null or length(published_run_id) = 0 then
        raise exception 'RP2_PUBLISH_RUN_ID_MISSING';
    end if;
    perform pg_advisory_xact_lock(hashtext('rp2_publish:' || published_run_id));
    if block_rows = 0 and contrast_rows = 0 then
        raise exception 'RP2_PUBLISH_NOTHING_TO_PUBLISH';
    end if;
    if coalesce(run ->> 'code_commit', '') !~ '^[0-9a-f]{40}$' then
        raise exception 'RP2_PUBLISH_CODE_COMMIT_INVALID';
    end if;
    if coalesce(run ->> 'inputs_sha256', '') !~ '^[0-9a-f]{64}$'
       or coalesce(run ->> 'feature_registry_sha256', '') !~ '^[0-9a-f]{64}$'
       or coalesce(run ->> 'model_config_sha256', '') !~ '^[0-9a-f]{64}$'
       or coalesce(run ->> 'inference_config_sha256', '') !~ '^[0-9a-f]{64}$'
       or coalesce(run ->> 'common_mask_sha256', '') !~ '^[0-9a-f]{64}$'
       or coalesce(run ->> 'scientific_sha256', '') !~ '^[0-9a-f]{64}$' then
        raise exception 'RP2_PUBLISH_LINEAGE_INCOMPLETE:%', published_run_id;
    end if;
    if input_rows = 0 then
        raise exception 'RP2_PUBLISH_INPUTS_MISSING:%', published_run_id;
    end if;
    if coalesce(run ->> 'spec_version', '') is distinct from 'rp2-v3' then
        raise exception 'RP2_PUBLISH_SPEC_VERSION_UNEXPECTED:%:%',
            published_run_id, coalesce(run ->> 'spec_version', '(missing)');
    end if;
    if coalesce(run ->> 'branch_name', '') = '' then
        raise exception 'RP2_PUBLISH_BRANCH_MISSING:%', published_run_id;
    end if;
    if exists (
        select 1 from public.ingestion_runs r
        where r.run_id = published_run_id and r.status = 'PUBLISHED'
          and (r.code_commit is distinct from (run ->> 'code_commit')
            or r.inputs_sha256 is distinct from (run ->> 'inputs_sha256')
            or r.feature_registry_sha256 is distinct from (run ->> 'feature_registry_sha256')
            or r.model_config_sha256 is distinct from (run ->> 'model_config_sha256')
            or r.inference_config_sha256 is distinct from (run ->> 'inference_config_sha256')
            or r.common_mask_sha256 is distinct from (run ->> 'common_mask_sha256')
            or r.scientific_sha256 is distinct from (run ->> 'scientific_sha256')
            or r.spec_version is distinct from (run ->> 'spec_version')
            or r.branch_name is distinct from (run ->> 'branch_name')
            or r.note is distinct from (run ->> 'note')
            or r.input_count is distinct from input_rows)
    ) then
        raise exception 'RP2_PUBLISH_RUN_ID_IMMUTABLE:%', published_run_id;
    end if;
    if exists (
        select 1 from jsonb_array_elements(coalesce(payload -> 'contrasts', '[]'::jsonb)) as item
        join public.rp2_contrast_results c
          on c.run_id = published_run_id
         and c.role = item ->> 'role'
         and c.model_family = item ->> 'model_family'
         and c.base_information_set = item ->> 'base_information_set'
         and c.expanded_information_set = item ->> 'expanded_information_set'
        where c.estimate is distinct from (item ->> 'estimate')::double precision
           or c.ci_low is distinct from (item ->> 'ci_low')::double precision
           or c.ci_high is distinct from (item ->> 'ci_high')::double precision
           or c.p_value is distinct from (item ->> 'p_value')::double precision
           or c.sessions is distinct from (item ->> 'sessions')::integer
           or c.block_length is distinct from (item ->> 'block_length')::integer
           or c.mde is distinct from (item ->> 'mde')::double precision
           or c.equivalence_bound is distinct from (item ->> 'equivalence_bound')::double precision
           or c.common_mask_sha256 is distinct from (item ->> 'common_mask_sha256')
    ) then
        raise exception 'RP2_PUBLISH_CONTRAST_IMMUTABLE:%', published_run_id;
    end if;
    if exists (
        select 1 from jsonb_array_elements(coalesce(payload -> 'blocks', '[]'::jsonb)) as item
        join public.rp2_block_results b
          on b.run_id = published_run_id and b.block_id = item ->> 'block_id'
        where b.status is distinct from (item ->> 'status')
           or b.verdict is distinct from (item ->> 'verdict')
           or b.document is distinct from (item ->> 'document')
           or b.artifact_sha256 is distinct from (item ->> 'artifact_sha256')
    ) then
        raise exception 'RP2_PUBLISH_BLOCK_IMMUTABLE:%', published_run_id;
    end if;
    if exists (
        select 1 from jsonb_array_elements(coalesce(payload -> 'inputs', '[]'::jsonb)) as item
        join public.ingestion_inputs i
          on i.run_id = published_run_id and i.input_name = item ->> 'input_name'
        where i.path is distinct from (item ->> 'path')
           or i.provider is distinct from (item ->> 'provider')
           or i.sha256 is distinct from (item ->> 'sha256')
           or i.bytes is distinct from (item ->> 'bytes')::bigint
           or i.rows is distinct from nullif(item ->> 'rows', '')::bigint
           or i.schema_sha256 is distinct from (item ->> 'schema_sha256')
           or i.time_min is distinct from (item ->> 'time_min')
           or i.time_max is distinct from (item ->> 'time_max')
    ) then
        raise exception 'RP2_PUBLISH_INPUT_IMMUTABLE:%', published_run_id;
    end if;
    if exists (select 1 from public.ingestion_runs r
               where r.run_id = published_run_id and r.status = 'PUBLISHED')
       and exists (
        (select item ->> 'role' as role, item ->> 'model_family' as model_family,
                item ->> 'base_information_set' as base_information_set,
                item ->> 'expanded_information_set' as expanded_information_set
         from jsonb_array_elements(coalesce(payload -> 'contrasts', '[]'::jsonb)) as item
         except
         select c.role, c.model_family, c.base_information_set, c.expanded_information_set
         from public.rp2_contrast_results c where c.run_id = published_run_id)
        union all
        (select c.role, c.model_family, c.base_information_set, c.expanded_information_set
         from public.rp2_contrast_results c where c.run_id = published_run_id
         except
         select item ->> 'role', item ->> 'model_family',
                item ->> 'base_information_set', item ->> 'expanded_information_set'
         from jsonb_array_elements(coalesce(payload -> 'contrasts', '[]'::jsonb)) as item)
    ) then
        raise exception 'RP2_PUBLISH_CONTRAST_SET_CHANGED:%', published_run_id;
    end if;
    if exists (select 1 from public.ingestion_runs r
               where r.run_id = published_run_id and r.status = 'PUBLISHED')
       and exists (
        (select item ->> 'block_id' as block_id
         from jsonb_array_elements(coalesce(payload -> 'blocks', '[]'::jsonb)) as item
         except
         select b.block_id from public.rp2_block_results b where b.run_id = published_run_id)
        union all
        (select b.block_id from public.rp2_block_results b where b.run_id = published_run_id
         except
         select item ->> 'block_id'
         from jsonb_array_elements(coalesce(payload -> 'blocks', '[]'::jsonb)) as item)
    ) then
        raise exception 'RP2_PUBLISH_BLOCK_SET_CHANGED:%', published_run_id;
    end if;
    if exists (select 1 from public.ingestion_runs r
               where r.run_id = published_run_id and r.status = 'PUBLISHED')
       and exists (
        (select item ->> 'input_name' as input_name
         from jsonb_array_elements(coalesce(payload -> 'inputs', '[]'::jsonb)) as item
         except
         select i.input_name from public.ingestion_inputs i where i.run_id = published_run_id)
        union all
        (select i.input_name from public.ingestion_inputs i where i.run_id = published_run_id
         except
         select item ->> 'input_name'
         from jsonb_array_elements(coalesce(payload -> 'inputs', '[]'::jsonb)) as item)
    ) then
        raise exception 'RP2_PUBLISH_INPUT_SET_CHANGED:%', published_run_id;
    end if;
    if exists (select 1 from public.ingestion_runs r
               where r.run_id = published_run_id and r.status = 'PUBLISHED') then
        return jsonb_build_object('run_id', published_run_id, 'status', 'ALREADY_PUBLISHED',
                                  'contrasts', contrast_rows);
    end if;
    insert into public.ingestion_runs (
        run_id, started_at, status, code_commit, inputs_sha256, input_count, rows_published,
        note, spec_version, branch_name, feature_registry_sha256, model_config_sha256,
        inference_config_sha256, common_mask_sha256, scientific_sha256)
    values (published_run_id, now(), 'RUNNING', run ->> 'code_commit', run ->> 'inputs_sha256',
        input_rows, 0, run ->> 'note', run ->> 'spec_version', run ->> 'branch_name',
        run ->> 'feature_registry_sha256', run ->> 'model_config_sha256',
        run ->> 'inference_config_sha256', run ->> 'common_mask_sha256',
        run ->> 'scientific_sha256')
    on conflict (run_id) do update set
        status = 'RUNNING', code_commit = excluded.code_commit,
        inputs_sha256 = excluded.inputs_sha256, input_count = excluded.input_count,
        note = excluded.note, spec_version = excluded.spec_version,
        branch_name = excluded.branch_name,
        feature_registry_sha256 = excluded.feature_registry_sha256,
        model_config_sha256 = excluded.model_config_sha256,
        inference_config_sha256 = excluded.inference_config_sha256,
        common_mask_sha256 = excluded.common_mask_sha256,
        scientific_sha256 = excluded.scientific_sha256;
    insert into public.ingestion_inputs (
        run_id, input_name, path, provider, sha256, bytes, rows, schema_sha256, time_min, time_max)
    select published_run_id, item ->> 'input_name', item ->> 'path', item ->> 'provider',
        item ->> 'sha256', (item ->> 'bytes')::bigint, nullif(item ->> 'rows', '')::bigint,
        item ->> 'schema_sha256', item ->> 'time_min', item ->> 'time_max'
    from jsonb_array_elements(coalesce(payload -> 'inputs', '[]'::jsonb)) as item
    on conflict (run_id, input_name) do update set
        path = excluded.path, provider = excluded.provider, sha256 = excluded.sha256,
        bytes = excluded.bytes, rows = excluded.rows,
        schema_sha256 = excluded.schema_sha256, time_min = excluded.time_min,
        time_max = excluded.time_max;
    select jsonb_object_agg(b.block_id, b.run_id) into superseded
    from public.rp2_block_results b
    where b.is_current and b.run_id is distinct from published_run_id
      and b.block_id in (select item ->> 'block_id'
                         from jsonb_array_elements(coalesce(payload -> 'blocks', '[]'::jsonb)) as item);
    update public.rp2_block_results r set is_current = false
    where r.is_current and r.block_id in (
        select item ->> 'block_id'
        from jsonb_array_elements(coalesce(payload -> 'blocks', '[]'::jsonb)) as item);
    insert into public.rp2_block_results (
        block_id, run_id, status, verdict, document, artifact_sha256, supersedes_run_id, is_current)
    select item ->> 'block_id', published_run_id, item ->> 'status', item ->> 'verdict',
        item ->> 'document', item ->> 'artifact_sha256',
        coalesce(superseded, '{}'::jsonb) ->> (item ->> 'block_id'), true
    from jsonb_array_elements(coalesce(payload -> 'blocks', '[]'::jsonb)) as item
    on conflict (block_id, run_id) do update set
        status = excluded.status, verdict = excluded.verdict, document = excluded.document,
        artifact_sha256 = excluded.artifact_sha256,
        supersedes_run_id = excluded.supersedes_run_id, is_current = true;
    update public.rp2_contrast_results c set is_current = false
    where c.is_current
      and (c.role, c.model_family, c.base_information_set, c.expanded_information_set) in (
          select item ->> 'role', item ->> 'model_family',
                 item ->> 'base_information_set', item ->> 'expanded_information_set'
          from jsonb_array_elements(coalesce(payload -> 'contrasts', '[]'::jsonb)) as item);
    insert into public.rp2_contrast_results (
        run_id, role, model_family, base_information_set, expanded_information_set,
        estimate, ci_low, ci_high, p_value, sessions, block_length, mde, equivalence_bound,
        common_mask_sha256, is_current)
    select published_run_id, item ->> 'role', item ->> 'model_family',
        item ->> 'base_information_set', item ->> 'expanded_information_set',
        (item ->> 'estimate')::double precision, (item ->> 'ci_low')::double precision,
        (item ->> 'ci_high')::double precision, (item ->> 'p_value')::double precision,
        (item ->> 'sessions')::integer, (item ->> 'block_length')::integer,
        (item ->> 'mde')::double precision, (item ->> 'equivalence_bound')::double precision,
        item ->> 'common_mask_sha256', true
    from jsonb_array_elements(coalesce(payload -> 'contrasts', '[]'::jsonb)) as item
    on conflict (run_id, role, model_family, base_information_set, expanded_information_set)
    do update set
        estimate = excluded.estimate, ci_low = excluded.ci_low, ci_high = excluded.ci_high,
        p_value = excluded.p_value, sessions = excluded.sessions,
        block_length = excluded.block_length, mde = excluded.mde,
        equivalence_bound = excluded.equivalence_bound,
        common_mask_sha256 = excluded.common_mask_sha256, is_current = true;
    update public.ingestion_runs
    set rows_published = block_rows + contrast_rows, status = 'PUBLISHED', completed_at = now()
    where run_id = published_run_id;
    return jsonb_build_object('run_id', published_run_id, 'inputs', input_rows,
        'blocks', block_rows, 'contrasts', contrast_rows, 'status', 'PUBLISHED');
end;
$$;
comment on function public.publish_rp2_v3(jsonb) is
    'Publish one RP2-v3 run atomically: the run, its inputs, its block results and its contrasts, with the previous current rows stood down. Raises rather than half-publishing.';
revoke all on function public.publish_rp2_v3(jsonb) from public;
revoke all on function public.publish_rp2_v3(jsonb) from anon, authenticated;
grant execute on function public.publish_rp2_v3(jsonb) to service_role;
create or replace function public.record_rp2_v3_failure(failed_run_id text, reason text)
returns void
language sql
security invoker
set search_path = public
as $$
    insert into public.ingestion_runs (run_id, started_at, status, input_count, rows_published,
                                       attempt_log)
    values (failed_run_id, now(), 'FAILED', 0, 0, now()::text || ' ' || reason)
    on conflict (run_id) do update set
        status = case when public.ingestion_runs.status = 'PUBLISHED' then 'PUBLISHED' else 'FAILED' end,
        attempt_log = concat_ws(
            E'\n', nullif(public.ingestion_runs.attempt_log, ''), excluded.attempt_log
        ),
        completed_at = case
            when public.ingestion_runs.status = 'PUBLISHED' then public.ingestion_runs.completed_at
            else now()
        end;
$$;
revoke all on function public.record_rp2_v3_failure(text, text) from public;
revoke all on function public.record_rp2_v3_failure(text, text) from anon, authenticated;
grant execute on function public.record_rp2_v3_failure(text, text) to service_role;
