create table if not exists public.b1_mock_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  attempted_at timestamptz not null default now(),
  attempt_version text not null default 'b1-weekly-v1',
  listening_correct smallint not null check (listening_correct between 0 and 2),
  reading_correct smallint not null check (reading_correct between 0 and 2),
  grammar_correct smallint not null check (grammar_correct between 0 and 3),
  constraint b1_mock_attempt_version_length check (char_length(attempt_version) between 1 and 32)
);

create index if not exists b1_mock_attempts_user_time_idx
  on public.b1_mock_attempts (user_id, attempted_at desc);

alter table public.b1_mock_attempts enable row level security;
revoke all on table public.b1_mock_attempts from anon, authenticated;
grant select, insert on table public.b1_mock_attempts to authenticated;

create policy "Users can read own B1 mock attempts"
  on public.b1_mock_attempts for select to authenticated
  using ((select auth.uid()) = user_id);

create policy "Users can insert own B1 mock attempts"
  on public.b1_mock_attempts for insert to authenticated
  with check ((select auth.uid()) = user_id);
