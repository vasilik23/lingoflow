-- Checked answer counts only; no audio, transcript or free-form answers.
create table public.b2_listening_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  attempt_id uuid not null,
  material_id text not null check (material_id = 'hybrid-work-message'),
  content_version smallint not null check (content_version = 1),
  correct smallint not null check (correct between 0 and 3),
  missed_mask smallint not null check (missed_mask between 0 and 7),
  completed_at timestamptz not null default now(),
  unique(user_id, attempt_id),
  check (correct = 3 - ((missed_mask & 1) + ((missed_mask >> 1) & 1) + ((missed_mask >> 2) & 1)))
);
create index b2_listening_owner_latest_idx on public.b2_listening_attempts(user_id, completed_at desc, attempt_id desc);
alter table public.b2_listening_attempts enable row level security;
revoke all on public.b2_listening_attempts from public, anon, authenticated;
grant select on public.b2_listening_attempts to authenticated;
grant insert (user_id, attempt_id, material_id, content_version, correct, missed_mask) on public.b2_listening_attempts to authenticated;
create policy b2_listening_owner_read on public.b2_listening_attempts for select to authenticated using ((select auth.uid()) = user_id);
create policy b2_listening_owner_insert on public.b2_listening_attempts for insert to authenticated with check ((select auth.uid()) = user_id);
comment on table public.b2_listening_attempts is 'Owner-scoped B2 listening practice, graded by Django. Ordinary users can report their own results through the Data API; not a certified exam score. Immutable; account deletion cascades.';
