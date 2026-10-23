-- Additive metadata only. No warning, expiry job, backfill or account deletion.
alter table public.profiles
  add column last_request_at timestamptz,
  add column activity_tracking_started_at timestamptz;
alter table public.user_feedback add column closed_at timestamptz;

-- RLS does not protect TRUNCATE. Keep only operations used by owner policies.
revoke all on public.profiles from anon;
revoke delete, truncate, references, trigger on public.profiles from authenticated;
grant select, insert, update on public.profiles to authenticated;

create function private.stamp_profile_activity()
returns trigger language plpgsql security invoker
set search_path = pg_catalog
as $$
declare stamped timestamptz := clock_timestamp();
begin
  if tg_op = 'INSERT' then
    new.last_request_at := null;
    new.activity_tracking_started_at := null;
    if auth.uid() = new.id then
      new.last_request_at := stamped;
      new.activity_tracking_started_at := stamped;
    end if;
  else
    -- Owner writes count as use. Client timestamps are never accepted.
    new.last_request_at := old.last_request_at;
    new.activity_tracking_started_at := old.activity_tracking_started_at;
    if auth.uid() = new.id then
      new.last_request_at := greatest(old.last_request_at, stamped);
      new.activity_tracking_started_at := coalesce(old.activity_tracking_started_at, stamped);
    end if;
  end if;
  return new;
end;
$$;
revoke all on function private.stamp_profile_activity() from public, anon, authenticated;
create trigger stamp_profile_activity before insert or update on public.profiles
for each row execute function private.stamp_profile_activity();

-- Invoker rights + existing owner SELECT/UPDATE RLS. No caller-supplied owner or clock.
-- Returns remaining throttle seconds, or zero if no owner profile exists.
create function public.record_account_activity()
returns integer language plpgsql security invoker
set search_path = pg_catalog
as $$
declare owner_id uuid := auth.uid(); last_seen timestamptz;
begin
  if owner_id is null then return 0; end if;
  update public.profiles set last_request_at = clock_timestamp()
    where id = owner_id and
      (last_request_at is null or last_request_at <= clock_timestamp() - interval '15 minutes');
  select last_request_at into last_seen from public.profiles where id = owner_id;
  if last_seen is null then return 0; end if;
  return greatest(1, least(900, ceil(extract(epoch from
    (last_seen + interval '15 minutes' - clock_timestamp())))::integer));
end;
$$;
revoke all on function public.record_account_activity() from public, anon;
grant execute on function public.record_account_activity() to authenticated;

create function private.stamp_feedback_closure()
returns trigger language plpgsql security invoker
set search_path = pg_catalog
as $$
begin
  if new.status <> 'resolved' then
    new.closed_at := null;
  elsif tg_op = 'INSERT' then
    new.closed_at := clock_timestamp();
  elsif old.status is distinct from 'resolved' then
    new.closed_at := clock_timestamp();
  else
    -- Keep unknown historic closure dates NULL; editing does not invent one.
    new.closed_at := old.closed_at;
  end if;
  return new;
end;
$$;
revoke all on function private.stamp_feedback_closure() from public, anon, authenticated;
create trigger stamp_feedback_closure before insert or update on public.user_feedback
for each row execute function private.stamp_feedback_closure();

comment on column public.profiles.last_request_at is
  'Database-stamped account use; requests are coalesced for up to 15 minutes. Not a complete access log.';
comment on column public.profiles.activity_tracking_started_at is
  'First observed use with activity tracking. NULL for unobserved/legacy users; not evidence of gap-free coverage.';
comment on column public.user_feedback.closed_at is
  'Database-stamped transition to resolved; reset on reopen. Legacy resolved rows remain NULL.';
notify pgrst, 'reload schema';

-- Operator-only, invoker-rights inventory. No personal text or email, no writes.
create function private.retention_review_snapshot()
returns jsonb language plpgsql security invoker
set search_path = pg_catalog
as $$
declare captured timestamptz := clock_timestamp(); payload jsonb;
begin
  if (select count(*) from auth.users) + (select count(*) from public.user_feedback) > 10000 then
    raise exception 'retention_inventory_requires_pagination' using errcode = '54000';
  end if;
  select jsonb_build_object(
    'version', 1,
    'captured_at', to_char(captured at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
    'accounts', coalesce((select jsonb_agg(jsonb_build_object(
      'user_id', u.id,
      'created_at', to_char(u.created_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
      -- Coalescing bound avoids interpreting unrecorded requests in the 15-minute
      -- window as inactivity. Auth sign-in and lesson dates are additional bounds.
      'last_activity_at', to_char(least(captured, greatest(u.created_at, u.last_sign_in_at,
        p.last_request_at + interval '15 minutes',
        (p.last_active_date + 1)::timestamp at time zone 'UTC')) at time zone 'UTC',
        'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
      'activity_complete', false,
      'tracking_started_at', to_char(p.activity_tracking_started_at at time zone 'UTC',
        'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
      'warning', null
    ) order by u.id) from auth.users u left join public.profiles p on p.id=u.id), '[]'::jsonb),
    'feedback', coalesce((select jsonb_agg(jsonb_build_object(
      'id', f.id, 'status', f.status,
      'created_at', to_char(f.created_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
      'closed_at', to_char(f.closed_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')
    ) order by f.id) from public.user_feedback f), '[]'::jsonb)
  ) into payload;
  return payload;
end;
$$;
revoke all on function private.retention_review_snapshot() from public, anon, authenticated, service_role;
-- Access remains with the database operator/owner, not the public Data API.
