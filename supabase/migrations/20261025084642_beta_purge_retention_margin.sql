-- Daily execution needs a one-day margin to stay within a 30-day target.
-- Scheduler downtime is still an operational exception, not an erasure guarantee.
create or replace function private.beta_purge() returns void language sql security invoker
set search_path=pg_catalog as $$
 delete from private.beta_requests where observed_at <= now()-interval '29 days';
 delete from private.beta_attempts where reserved_at <= now()-interval '29 days';
 delete from private.beta_members where expires_at <= now();
$$;
revoke all on function private.beta_purge() from public,anon,authenticated;
grant execute on function private.beta_purge() to service_role;
