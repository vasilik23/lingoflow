-- Whitelisted aggregate-only JSON, even for direct Data API callers.
create or replace function public.valid_b1_run_results(items jsonb)
returns boolean language plpgsql immutable security invoker set search_path = '' as $$
declare item jsonb; position integer := 0; field text;
  part_ids text[] := array['listening','reading','grammar','writing','speaking'];
begin
  if jsonb_typeof(items) is distinct from 'array' then return false; end if;
  if jsonb_array_length(items) <> 5 then return false; end if;
  for item in select value from jsonb_array_elements(items) loop
    position := position + 1;
    if jsonb_typeof(item) is distinct from 'object' then return false; end if;
    if item->>'id' is distinct from part_ids[position] then return false; end if;
    if not item ?& array['id','status','timed_out'] then return false; end if;
    if jsonb_typeof(item->'timed_out') not in ('boolean','null') then return false; end if;
    if item->>'status' = 'scored' and position <= 3 then
      if (item - array['id','status','timed_out','correct','total','incorrect','unanswered']) <> '{}'::jsonb then return false; end if;
      foreach field in array array['correct','total','incorrect','unanswered'] loop
        if jsonb_typeof(item->field) is distinct from 'number' or (item->>field) !~ '^[0-9]{1,2}$' then return false; end if;
      end loop;
      if (item->>'total')::integer not between 1 and 64 or
         (item->>'correct')::integer + (item->>'incorrect')::integer + (item->>'unanswered')::integer <> (item->>'total')::integer then return false; end if;
    elsif item->>'status' = 'skipped' or (item->>'status' = 'self_review' and position > 3) then
      if (item - array['id','status','timed_out']) <> '{}'::jsonb then return false; end if;
    else return false;
    end if;
  end loop;
  return true;
end;
$$;
revoke all on function public.valid_b1_run_results(jsonb) from public, anon;
grant execute on function public.valid_b1_run_results(jsonb) to authenticated;

create table public.b1_run_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  run_id uuid not null,
  variant_id text not null check (variant_id in ('b1-weekly-v1','b1-weekly-v2','b1-weekly-v3')),
  content_version smallint not null check (content_version between 1 and 1000),
  started_at timestamptz not null,
  finished_at timestamptz not null,
  results jsonb not null check (public.valid_b1_run_results(results)),
  constraint b1_run_time_check check (finished_at >= started_at and finished_at - started_at <= interval '4 hours'),
  constraint b1_runs_user_run_key unique (user_id,run_id)
);
create index b1_runs_user_time_idx on public.b1_run_attempts (user_id, finished_at desc);
alter table public.b1_run_attempts enable row level security;
revoke all on table public.b1_run_attempts from anon, authenticated;
grant select, insert on table public.b1_run_attempts to authenticated;
create policy b1_runs_owner_read on public.b1_run_attempts for select to authenticated using ((select auth.uid()) = user_id);
create policy b1_runs_owner_insert on public.b1_run_attempts for insert to authenticated with check ((select auth.uid()) = user_id);
comment on table public.b1_run_attempts is 'Five-part B1 run aggregates only; no responses, essays, transcripts or recordings. Immutable and owner-scoped.';
