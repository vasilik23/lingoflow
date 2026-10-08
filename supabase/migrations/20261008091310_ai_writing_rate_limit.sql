-- AI writing: ten checks per owner per rolling 24-hour window.
-- Existing RPC auth.uid guard, empty search_path, private RLS and grants retained.
alter table private.api_mutation_buckets
  drop constraint if exists api_mutation_buckets_action_check;

alter table private.api_mutation_buckets
  add constraint api_mutation_buckets_action_check
  check (action in ('answer', 'profile', 'sm2', 'dictionary', 'bookmark', 'draft', 'result', 'feedback', 'ai_writing'));

create or replace function public.consume_api_mutation(p_action text)
returns table(allowed boolean, retry_after integer)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_limit integer;
  v_window integer := 60;
  v_now timestamptz := clock_timestamp();
  v_attempts integer;
  v_started timestamptz;
begin
  if v_user_id is null then
    raise insufficient_privilege using message = 'authentication required';
  end if;

  v_limit := case p_action
    when 'answer' then 180
    when 'profile' then 30
    when 'sm2' then 180
    when 'dictionary' then 90
    when 'bookmark' then 90
    when 'draft' then 180
    when 'result' then 120
    when 'feedback' then 20
    when 'ai_writing' then 10
    else null
  end;
  if v_limit is null then
    raise invalid_parameter_value using message = 'unsupported mutation action';
  end if;

  if p_action = 'ai_writing' then
    v_window := 86400;
  end if;

  insert into private.api_mutation_buckets as bucket
    (user_id, action, window_started_at, attempts)
  values (v_user_id, p_action, v_now, 1)
  on conflict (user_id, action) do update
  set
    attempts = case
      when bucket.window_started_at <= v_now - make_interval(secs => v_window) then 1
      else bucket.attempts + 1
    end,
    window_started_at = case
      when bucket.window_started_at <= v_now - make_interval(secs => v_window) then v_now
      else bucket.window_started_at
    end
  returning bucket.attempts, bucket.window_started_at
  into v_attempts, v_started;

  allowed := v_attempts <= v_limit;
  retry_after := greatest(
    1,
    ceil(extract(epoch from (v_started + make_interval(secs => v_window) - v_now)))::integer
  );
  return next;
end;
$$;

revoke all on function public.consume_api_mutation(text) from public, anon;
grant execute on function public.consume_api_mutation(text) to authenticated;
