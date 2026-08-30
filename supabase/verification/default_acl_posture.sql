-- Read-only ownership/default-ACL audit. It does not inspect scientific rows.
select
    current_user as session_user,
    pg_has_role(current_user, 'supabase_admin', 'SET') as can_set_supabase_admin,
    count(*) filter (where r.rolname = 'postgres') as postgres_owned,
    count(*) filter (where r.rolname <> 'postgres') as non_postgres_owned
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
join pg_roles r on r.oid = c.relowner
where n.nspname in ('public', 'api')
  and c.relkind in ('r', 'p', 'v', 'm', 'S', 'f');

select
    r.rolname as owner_name,
    n.nspname as schema_name,
    d.defaclobjtype,
    d.defaclacl::text as acl
from pg_default_acl d
join pg_roles r on r.oid = d.defaclrole
left join pg_namespace n on n.oid = d.defaclnamespace
where r.rolname in ('postgres', 'supabase_admin')
  and coalesce(n.nspname, '') in ('', 'public', 'api')
order by 1, 2, 3;
