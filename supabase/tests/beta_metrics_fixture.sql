-- ONLY an empty disposable PostgreSQL test database, not a Supabase project.
create role anon;
create role authenticated;
create role service_role bypassrls;
create schema private;
create schema auth;
create table auth.users(id uuid primary key);
create table public.lesson_completions(user_id uuid,lesson_id text,plan_date date,cards_total int,cards_known int);
create table public.lesson_result_events(user_id uuid,event_id uuid,lesson_id text);
grant select on public.lesson_completions,public.lesson_result_events to service_role;
