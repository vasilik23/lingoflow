-- Run on an isolated fixture database with this migration and production-shaped
-- auth.users / lesson_completions / lesson_result_events, never on learner data.
\set ON_ERROR_STOP on
begin;
create function pg_temp.assert(ok boolean, message text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception '%',message; end if; end $$;
insert into auth.users(id) values('00000000-0000-0000-0000-000000000001'),('00000000-0000-0000-0000-000000000002');
insert into private.beta_members(user_id,cohort,expires_at)
values('00000000-0000-0000-0000-000000000001','fixture',now()+interval '7 days');
select pg_temp.assert(not has_function_privilege('anon','public.beta_reserve_attempt(uuid,text,text)','execute'),'anon must not reserve');
select pg_temp.assert(not has_function_privilege('authenticated','public.beta_observe_request(uuid,uuid,text,text,text,integer,integer,uuid,boolean,boolean,integer,integer)','execute'),'learner must not forge requests');
select pg_temp.assert(not has_function_privilege('authenticated','public.beta_finish_attempt(uuid,uuid,text)','execute'),'learner must not finish');
select pg_temp.assert(not has_function_privilege('authenticated','private.beta_report(timestamptz,timestamptz)','execute'),'learner must not export');
select pg_temp.assert(not has_table_privilege('authenticated','private.beta_members','select,insert,update,delete,truncate'),'membership operator only');
select pg_temp.assert(not has_table_privilege('anon','private.beta_requests','select,insert,update,delete,truncate'),'request table operator only');
select pg_temp.assert((select bool_and(relrowsecurity) from pg_class where oid in ('private.beta_members'::regclass,'private.beta_attempts'::regclass,'private.beta_requests'::regclass)),'RLS required');
set local role service_role;
select public.beta_reserve_attempt('00000000-0000-0000-0000-000000000001','quiz',repeat('a',40)) as a \gset
select pg_temp.assert(public.beta_reserve_attempt('00000000-0000-0000-0000-000000000001','quiz',repeat('a',40))=:'a','refresh reuses reservation');
select pg_temp.assert(public.beta_reserve_attempt('00000000-0000-0000-0000-000000000002','quiz',repeat('a',40)) is null,'nonmember ignored');
select pg_temp.assert((private.beta_report(now()-interval '1 day',now()+interval '1 second')->'attempts'->0->>'started')::int=0,'GET reservation not a start');
select pg_temp.assert(public.beta_finish_attempt('00000000-0000-0000-0000-000000000002',:'a',repeat('a',40)) is null,'owner isolation');
select public.beta_finish_attempt('00000000-0000-0000-0000-000000000001',:'a',repeat('a',40)) as finished \gset
select pg_temp.assert(public.beta_finish_attempt('00000000-0000-0000-0000-000000000001',:'a',repeat('a',40))=:'finished'::timestamptz,'final retry timestamp stable');
select public.beta_observe_request('00000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',repeat('a',40),'lesson','POST',200,15,:'a',true,false,7,5);
select public.beta_observe_request('00000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',repeat('a',40),'lesson','POST',200,15,:'a',true,false,7,5);
select pg_temp.assert((select count(*) from private.beta_requests)=1,'transport replay deduplicates');
select pg_temp.assert((private.beta_report(now()-interval '1 day',now()+interval '1 second')->'attempts'->0->>'pending_confirmation')::int=1,'offline completion pending, not lost');
select public.beta_reserve_attempt('00000000-0000-0000-0000-000000000001','quiz',repeat('a',40)) as b \gset
select pg_temp.assert(:'a'<>:'b','B does not replace pending A');
reset role;
insert into public.lesson_completions values('00000000-0000-0000-0000-000000000001','quiz',(now() at time zone 'UTC')::date,7,6);
set local role service_role;
select public.beta_finish_attempt('00000000-0000-0000-0000-000000000001',:'b',repeat('a',40));
select public.beta_observe_request('00000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000002',repeat('a',40),'lesson','POST',200,25,:'b',true,true,7,6);
select pg_temp.assert((private.beta_report(now()-interval '1 day',now()+interval '1 second')->'attempts'->0->>'saved')::int=1,'B saved does not hide pending A');
reset role;
insert into public.lesson_result_events values('00000000-0000-0000-0000-000000000001',:'a','quiz');
set local role service_role;
select pg_temp.assert((private.beta_report(now()-interval '1 day',now()+interval '1 second')->'attempts'->0->>'saved')::int=2,'late immutable result reconciles A');
select pg_temp.assert((private.beta_report(now()-interval '1 day',now()+interval '1 second')->'attempts'->0->>'pending_confirmation')::int=0,'no outstanding confirmation');
select pg_temp.assert((private.beta_report(now()-interval '1 day',now()+interval '1 second')->'attempts'->0->>'started')::int=2,'retry adds no attempts');
select pg_temp.assert(private.beta_report(now()-interval '1 day',now()+interval '1 second')->>'lost_results' is null,'unknown losses remain null');
update private.beta_requests set observed_at=now()-interval '31 days';
update private.beta_attempts set reserved_at=now()-interval '31 days';
select private.beta_purge();
select pg_temp.assert((select count(*) from private.beta_requests)=0,'old requests purged');
select pg_temp.assert((select count(*) from private.beta_attempts)=0,'old attempts purged');
delete from private.beta_members;
select pg_temp.assert(public.beta_reserve_attempt('00000000-0000-0000-0000-000000000001','quiz',repeat('a',40)) is null,'withdrawal stops future collection');
rollback;
