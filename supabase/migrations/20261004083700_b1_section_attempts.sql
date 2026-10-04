create table if not exists public.b1_section_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  attempt_id uuid not null default gen_random_uuid(),
  attempted_at timestamptz not null default now(),
  attempt_version text not null,
  section_id text not null,
  correct smallint not null,
  total smallint not null,
  constraint b1_section_attempt_version_length check (char_length(attempt_version) between 1 and 32),
  constraint b1_section_attempt_section check (section_id in ('listening', 'reading', 'grammar')),
  constraint b1_section_attempt_score check (total between 1 and 64 and correct between 0 and total),
  constraint b1_section_attempts_user_attempt_key unique (user_id, attempt_id)
);

create index if not exists b1_section_attempts_user_time_idx
  on public.b1_section_attempts (user_id, attempted_at desc);

alter table public.b1_section_attempts enable row level security;
revoke all on table public.b1_section_attempts from anon, authenticated;
grant select, insert on table public.b1_section_attempts to authenticated;

drop policy if exists "Users can read own B1 section attempts" on public.b1_section_attempts;
create policy "Users can read own B1 section attempts"
  on public.b1_section_attempts for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "Users can insert own B1 section attempts" on public.b1_section_attempts;
create policy "Users can insert own B1 section attempts"
  on public.b1_section_attempts for insert to authenticated
  with check ((select auth.uid()) = user_id);

comment on table public.b1_section_attempts is
  'Owner-scoped aggregate results for objective timed B1 sections. Selected answers and free production are never stored.';
