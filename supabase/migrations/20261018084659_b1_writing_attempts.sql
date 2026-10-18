-- Rehearsal metadata only: no essay, answers, transcript, recording or score columns.
create table public.b1_writing_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  attempt_id uuid not null,
  set_id text not null check (set_id in ('1','2','3')),
  content_version smallint not null check (content_version = 1),
  started_at timestamptz not null,
  finished_at timestamptz not null,
  timed_out boolean not null,
  remaining_seconds integer not null check (remaining_seconds between 0 and 4500),
  words_a integer not null check (words_a between 0 and 20000),
  words_b integer not null check (words_b between 0 and 20000),
  constraint b1_writing_owner_attempt_key unique (user_id, attempt_id),
  constraint b1_writing_time_check check (
    finished_at >= started_at and finished_at - started_at <= interval '75 minutes'
    and abs(extract(epoch from finished_at - started_at) + remaining_seconds - 4500) <= 1.01
    and (not timed_out or (remaining_seconds = 0 and finished_at - started_at >= interval '4499 seconds'))
  )
);
create index b1_writing_owner_time_idx on public.b1_writing_attempts(user_id, finished_at desc);
alter table public.b1_writing_attempts enable row level security;
revoke all on table public.b1_writing_attempts from public, anon, authenticated;
grant select, insert on table public.b1_writing_attempts to authenticated;
create policy b1_writing_owner_read on public.b1_writing_attempts for select to authenticated
  using ((select auth.uid()) = user_id);
create policy b1_writing_owner_insert on public.b1_writing_attempts for insert to authenticated
  with check ((select auth.uid()) = user_id and finished_at <= now() + interval '5 minutes');
comment on table public.b1_writing_attempts is 'Immutable browser-reported B1 writing rehearsal metadata. Not a verified exam score. Essays stay on device.';

-- Atomic idempotence, under the caller's RLS. An existing attempt cannot be overwritten.
create function public.save_b1_writing_attempt(attempt jsonb)
returns text language plpgsql security invoker set search_path = '' as $$
declare previous public.b1_writing_attempts; inserted integer;
begin
  if auth.uid() is null then raise exception 'Authentication required' using errcode = '42501'; end if;
  if jsonb_typeof(attempt) is distinct from 'object'
    or not attempt ?& array['attempt_id','set_id','content_version','started_at','finished_at','timed_out','remaining_seconds','words_a','words_b']
    or attempt - array['attempt_id','set_id','content_version','started_at','finished_at','timed_out','remaining_seconds','words_a','words_b'] <> '{}'::jsonb
    or jsonb_typeof(attempt->'attempt_id') is distinct from 'string'
    or jsonb_typeof(attempt->'set_id') is distinct from 'string'
    or jsonb_typeof(attempt->'started_at') is distinct from 'string'
    or jsonb_typeof(attempt->'finished_at') is distinct from 'string'
    or jsonb_typeof(attempt->'timed_out') is distinct from 'boolean'
    or jsonb_typeof(attempt->'content_version') is distinct from 'number'
    or jsonb_typeof(attempt->'remaining_seconds') is distinct from 'number'
    or jsonb_typeof(attempt->'words_a') is distinct from 'number'
    or jsonb_typeof(attempt->'words_b') is distinct from 'number'
    or attempt->>'content_version' !~ '^[0-9]+$'
    or attempt->>'remaining_seconds' !~ '^[0-9]+$'
    or attempt->>'words_a' !~ '^[0-9]+$'
    or attempt->>'words_b' !~ '^[0-9]+$'
  then raise exception 'Invalid metadata' using errcode = '22023'; end if;
  insert into public.b1_writing_attempts(user_id, attempt_id, set_id, content_version, started_at, finished_at, timed_out, remaining_seconds, words_a, words_b)
    values (auth.uid(), (attempt->>'attempt_id')::uuid, attempt->>'set_id', (attempt->>'content_version')::smallint,
      (attempt->>'started_at')::timestamptz, (attempt->>'finished_at')::timestamptz, (attempt->>'timed_out')::boolean,
      (attempt->>'remaining_seconds')::integer, (attempt->>'words_a')::integer, (attempt->>'words_b')::integer)
    on conflict (user_id, attempt_id) do nothing;
  get diagnostics inserted = row_count;
  if inserted = 1 then return 'saved'; end if;
  select * into strict previous from public.b1_writing_attempts
    where user_id = auth.uid() and attempt_id = (attempt->>'attempt_id')::uuid;
  if previous.set_id = attempt->>'set_id'
    and previous.content_version = (attempt->>'content_version')::smallint
    and previous.started_at = (attempt->>'started_at')::timestamptz
    and previous.finished_at = (attempt->>'finished_at')::timestamptz
    and previous.timed_out = (attempt->>'timed_out')::boolean
    and previous.remaining_seconds = (attempt->>'remaining_seconds')::integer
    and previous.words_a = (attempt->>'words_a')::integer
    and previous.words_b = (attempt->>'words_b')::integer
  then return 'duplicate'; end if;
  return 'conflict';
end;
$$;
revoke all on function public.save_b1_writing_attempt(jsonb) from public, anon;
grant execute on function public.save_b1_writing_attempt(jsonb) to authenticated;
