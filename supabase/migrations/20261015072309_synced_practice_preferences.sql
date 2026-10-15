-- Nullable intentionally: retain legacy browser preference until explicit save.
-- Existing owner-only profile SELECT/INSERT/UPDATE policies and grants apply.
alter table public.profiles add column practice_exclude_remote_work boolean;
comment on column public.profiles.practice_exclude_remote_work is
  'Account-wide practice exclusion; null means no server choice yet. Explicit false overrides legacy browser cookies. Last acknowledged write wins.';
