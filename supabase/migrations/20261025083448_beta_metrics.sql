-- Operator-only diagnostics. Empty membership means no collection.
create table private.beta_members (
  user_id uuid primary key references auth.users(id) on delete cascade,
  cohort text not null check (cohort ~ '^[a-z0-9-]{1,40}$'),
  enrolled_at timestamptz not null default now(),
  expires_at timestamptz not null,
  check (expires_at > enrolled_at and expires_at <= enrolled_at + interval '30 days')
);
create table private.beta_attempts (
  attempt_id uuid primary key default gen_random_uuid(),
  user_id uuid not null references private.beta_members(user_id) on delete cascade,
  cohort text not null, release_sha text not null check (release_sha ~ '^[0-9a-f]{40}$'),
  lesson_id text not null, reserved_at timestamptz not null default now(),
  started_at timestamptz, finish_requested_at timestamptz,
  projection_confirmed_at timestamptz
);
create index beta_attempt_owner on private.beta_attempts(user_id, lesson_id, reserved_at desc);
create table private.beta_requests (
  request_id uuid primary key,
  cohort text not null, release_sha text not null check (release_sha ~ '^[0-9a-f]{40}$'),
  observed_at timestamptz not null default now(),
  route_group text not null check (route_group in ('today','lesson','result')),
  method text not null check (method in ('GET','POST')),
  status integer not null check (status between 100 and 599),
  app_ms integer not null check (app_ms >= 0)
);
create index beta_requests_window on private.beta_requests(observed_at);
alter table private.beta_members enable row level security;
alter table private.beta_attempts enable row level security;
alter table private.beta_requests enable row level security;
revoke all on private.beta_members, private.beta_attempts, private.beta_requests from public, anon, authenticated;
grant usage on schema private to service_role;
grant select, insert, update, delete on private.beta_members, private.beta_attempts, private.beta_requests to service_role;

-- Service credential is held only by Django, never by a learner/browser.
-- Invoker rights: no privilege escalation and no caller-editable JWT metadata.
create function public.beta_reserve_attempt(p_owner uuid, p_lesson text, p_release text)
returns uuid language plpgsql security invoker set search_path = pg_catalog as $$
declare member private.beta_members; found_id uuid;
begin
  select * into member from private.beta_members
    where user_id = p_owner and enrolled_at <= now() and expires_at > now();
  if not found then return null; end if;
  if p_lesson !~ '^[a-z0-9-]{1,32}$' or p_release !~ '^[0-9a-f]{40}$' then
    raise exception 'Invalid diagnostic dimension';
  end if;
  -- Serialize reserve and finish for this owner+lesson; refresh/two tabs reuse
  -- an unfinished attempt instead of manufacturing new starts.
  perform pg_advisory_xact_lock(hashtextextended(p_owner::text || ':' || p_lesson, 0));
  select attempt_id into found_id from private.beta_attempts
    where user_id=p_owner and lesson_id=p_lesson and release_sha=p_release
      and cohort=member.cohort and finish_requested_at is null
      and reserved_at >= now() - interval '12 hours'
    order by reserved_at desc limit 1;
  if found_id is not null then return found_id; end if;
  insert into private.beta_attempts(user_id,cohort,release_sha,lesson_id)
    values(p_owner,member.cohort,p_release,p_lesson) returning attempt_id into found_id;
  return found_id;
end $$;

create function public.beta_observe_request(
 p_owner uuid, p_request uuid, p_release text, p_route text, p_method text,
 p_status integer, p_duration integer, p_attempt uuid default null,
 p_finished boolean default false, p_saved boolean default false,
 p_total integer default null, p_known integer default null
) returns boolean language plpgsql security invoker set search_path = pg_catalog as $$
declare member private.beta_members; attempt private.beta_attempts;
begin
  select * into member from private.beta_members
    where user_id=p_owner and enrolled_at <= now() and expires_at > now();
  if not found then return false; end if;
  insert into private.beta_requests(request_id,cohort,release_sha,route_group,method,status,app_ms)
    values(p_request,member.cohort,p_release,p_route,p_method,p_status,p_duration)
    on conflict(request_id) do nothing;
  if p_attempt is not null and p_route='lesson' and p_method='POST' and p_status=200 then
    select * into attempt from private.beta_attempts
      where attempt_id=p_attempt and user_id=p_owner and cohort=member.cohort
        and release_sha=p_release and reserved_at >= now()-interval '30 days';
    if found then
      perform pg_advisory_xact_lock(hashtextextended(p_owner::text || ':' || attempt.lesson_id, 0));
      update private.beta_attempts set
        started_at=coalesce(started_at,now()),
        finish_requested_at=case when p_finished then coalesce(finish_requested_at,now()) else finish_requested_at end,
        projection_confirmed_at=case when p_finished and p_saved and exists (
          select 1 from public.lesson_completions c where c.user_id=p_owner
            and c.lesson_id=attempt.lesson_id and c.plan_date=(now() at time zone 'UTC')::date
            and c.cards_total=p_total and c.cards_known=p_known
        ) then coalesce(projection_confirmed_at,now()) else projection_confirmed_at end
      where attempt_id=p_attempt;
    end if;
  end if;
  return true;
end $$;
revoke all on function public.beta_reserve_attempt(uuid,text,text) from public, anon, authenticated;
revoke all on function public.beta_observe_request(uuid,uuid,text,text,text,integer,integer,uuid,boolean,boolean,integer,integer) from public, anon, authenticated;
grant execute on function public.beta_reserve_attempt(uuid,text,text) to service_role;
grant execute on function public.beta_observe_request(uuid,uuid,text,text,text,integer,integer,uuid,boolean,boolean,integer,integer) to service_role;

-- Operator invokes daily before enabling collection; no scheduler is installed.
create function private.beta_purge() returns void language sql security invoker
set search_path = pg_catalog as $$
 delete from private.beta_requests where observed_at <= now()-interval '30 days';
 delete from private.beta_attempts where reserved_at <= now()-interval '30 days';
 delete from private.beta_members where expires_at <= now();
$$;
revoke all on function private.beta_purge() from public,anon,authenticated;
grant execute on function private.beta_purge() to service_role;

-- Exact millisecond frequencies; callers calculate nearest-rank p95 by scope.
-- No per-request identity, owner, lesson, answers or attempt IDs in exported JSON.
create function private.beta_report(p_since timestamptz, p_until timestamptz)
returns jsonb language sql stable security invoker set search_path = pg_catalog as $$
 select jsonb_build_object('schema_version',1,'latency_scope','django_app_before_collector',
  'end_to_end_ms',null,'field_inp_ms',null,'lost_results',null,
  'coverage','best_effort_received_only','since',p_since,'until',p_until,
  'requests',coalesce((select jsonb_agg(to_jsonb(t)) from (
    select cohort,release_sha,route_group,method,status,app_ms,count(*) as count
    from private.beta_requests where observed_at >= greatest(p_since,now()-interval '30 days') and observed_at < p_until
    group by cohort,release_sha,route_group,method,status,app_ms
  ) t),'[]'::jsonb),
  'attempts',coalesce((select jsonb_agg(to_jsonb(t)) from (
    select a.cohort,a.release_sha,
      count(*) filter(where a.started_at is not null) as started,
      count(*) filter(where a.finish_requested_at is not null) as finish_requested,
      count(*) filter(where a.projection_confirmed_at is not null or exists(
        select 1 from public.lesson_result_events e where e.user_id=a.user_id and e.event_id=a.attempt_id and e.lesson_id=a.lesson_id
      )) as saved,
      count(*) filter(where a.finish_requested_at is not null and a.projection_confirmed_at is null and not exists(
        select 1 from public.lesson_result_events e where e.user_id=a.user_id and e.event_id=a.attempt_id and e.lesson_id=a.lesson_id
      )) as pending_confirmation
    from private.beta_attempts a
    where a.reserved_at >= greatest(p_since,now()-interval '30 days') and a.reserved_at < p_until
    group by a.cohort,a.release_sha
  ) t),'[]'::jsonb));
$$;
revoke all on function private.beta_report(timestamptz,timestamptz) from public,anon,authenticated;
grant execute on function private.beta_report(timestamptz,timestamptz) to service_role;

-- Freeze the finalization timestamp before rendering a retryable queue payload.
-- Replay of the same final signed state gets the identical event ID/date/hash.
create function public.beta_finish_attempt(p_owner uuid,p_attempt uuid,p_release text)
returns timestamptz language plpgsql security invoker set search_path=pg_catalog as $$
declare item private.beta_attempts; stamped timestamptz;
begin
  select a.* into item from private.beta_attempts a join private.beta_members m using(user_id)
    where a.attempt_id=p_attempt and a.user_id=p_owner and a.release_sha=p_release
      and a.cohort=m.cohort and m.enrolled_at<=now() and m.expires_at>now()
      and a.reserved_at>=now()-interval '30 days';
  if not found then return null; end if;
  perform pg_advisory_xact_lock(hashtextextended(p_owner::text||':'||item.lesson_id,0));
  update private.beta_attempts set started_at=coalesce(started_at,now()),
    finish_requested_at=coalesce(finish_requested_at,now()) where attempt_id=p_attempt
    returning finish_requested_at into stamped;
  return stamped;
end $$;
revoke all on function public.beta_finish_attempt(uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.beta_finish_attempt(uuid,uuid,text) to service_role;
