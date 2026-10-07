-- Additive release: deploy before application code starts selecting the column.
-- Existing profiles keep a comparable 10/15/30 minute workload.
alter table public.profiles add column daily_goal_minutes smallint;
update public.profiles set daily_goal_minutes =
  case when daily_goal_lessons <= 2 then 10
       when daily_goal_lessons <= 4 then 15 else 30 end;
alter table public.profiles alter column daily_goal_minutes set default 15;
alter table public.profiles alter column daily_goal_minutes set not null;
alter table public.profiles add constraint profiles_daily_goal_minutes_check
  check (daily_goal_minutes in (10, 15, 30));
comment on column public.profiles.daily_goal_minutes is
  'Canonical daily learning budget; lesson count is retained for older clients.';
-- No new table, grants, policies or privileged functions. Existing owner-scoped
-- SELECT/INSERT/UPDATE policies protect this profile column as well.
