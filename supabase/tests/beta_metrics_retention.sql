-- Disposable local/CI database only. No production fixtures.
\set ON_ERROR_STOP on
begin;
create function pg_temp.assert(ok boolean,message text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception '%',message; end if; end $$;
insert into auth.users(id) values('00000000-0000-0000-0000-000000000010');
insert into private.beta_members(user_id,cohort,expires_at)
 values('00000000-0000-0000-0000-000000000010','retention-fixture',now()+interval '7 days');
insert into private.beta_attempts(user_id,cohort,release_sha,lesson_id,reserved_at)
 values('00000000-0000-0000-0000-000000000010','retention-fixture',repeat('a',40),'old',now()-interval '29 days 1 hour'),
       ('00000000-0000-0000-0000-000000000010','retention-fixture',repeat('a',40),'recent',now()-interval '28 days 23 hours');
insert into private.beta_requests(request_id,cohort,release_sha,route_group,method,status,app_ms,observed_at)
 values(gen_random_uuid(),'retention-fixture',repeat('a',40),'today','GET',200,10,now()-interval '29 days 1 hour'),
       (gen_random_uuid(),'retention-fixture',repeat('a',40),'today','GET',200,10,now()-interval '28 days 23 hours');
insert into public.lesson_completions values('00000000-0000-0000-0000-000000000010','keep-learning',current_date,7,5);
set local role service_role;
select private.beta_purge();
select pg_temp.assert((select count(*) from private.beta_attempts where cohort='retention-fixture')=1,'29-day margin');
select pg_temp.assert((select count(*) from private.beta_requests where cohort='retention-fixture')=1,'recent requests retained');
select pg_temp.assert((select count(*) from public.lesson_completions where lesson_id='keep-learning')=1,'learning results retained');
select private.beta_purge();
select pg_temp.assert((select count(*) from private.beta_attempts where cohort='retention-fixture')=1,'repeat purge idempotent');
rollback;
