alter table public.user_feedback
  add column if not exists priority text not null default 'normal';

alter table public.user_feedback
  drop constraint if exists user_feedback_priority_check;

alter table public.user_feedback
  add constraint user_feedback_priority_check
  check (priority in ('normal', 'high', 'blocking'));
