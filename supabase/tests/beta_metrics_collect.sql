\set ON_ERROR_STOP on
begin;
create function pg_temp.assert(ok boolean,message text) returns void language plpgsql as $$
begin if ok is distinct from true then raise exception '%',message; end if; end $$;
insert into auth.users(id) values('00000000-0000-0000-0000-000000000021'),('00000000-0000-0000-0000-000000000022');
insert into private.beta_members(user_id,cohort,expires_at)
 values('00000000-0000-0000-0000-000000000021','combined-fixture',now()+interval '1 day');
select pg_temp.assert(not has_function_privilege('authenticated','public.beta_collect_request(uuid,uuid,text,text,text,integer,integer,uuid,boolean,boolean,integer,integer,text)','execute'),'learner cannot call combined RPC');
select pg_temp.assert(not has_function_privilege('anon','public.beta_collect_request(uuid,uuid,text,text,text,integer,integer,uuid,boolean,boolean,integer,integer,text)','execute'),'anon cannot call combined RPC');
select pg_temp.assert(not (select prosecdef from pg_proc where oid='public.beta_collect_request(uuid,uuid,text,text,text,integer,integer,uuid,boolean,boolean,integer,integer,text)'::regprocedure),'invoker rights required');
set local role service_role;
select public.beta_collect_request('00000000-0000-0000-0000-000000000021','10000000-0000-0000-0000-000000000021',repeat('a',40),'lesson','GET',200,10,p_reserve_lesson:='quiz')->>'attempt_id' as a \gset
select pg_temp.assert(public.beta_collect_request('00000000-0000-0000-0000-000000000021','10000000-0000-0000-0000-000000000021',repeat('a',40),'lesson','GET',200,10,p_reserve_lesson:='quiz')->>'attempt_id'=:'a','transport retry reuses reservation');
select pg_temp.assert(public.beta_collect_request('00000000-0000-0000-0000-000000000021',gen_random_uuid(),repeat('a',40),'lesson','GET',200,10,p_reserve_lesson:='quiz')->>'attempt_id'=:'a','refresh reuses reservation');
select pg_temp.assert((select count(*) from private.beta_requests where cohort='combined-fixture')=2,'one observation per request');
select pg_temp.assert((select started_at is null from private.beta_attempts where attempt_id=:'a'),'GET not a start');
select public.beta_collect_request('00000000-0000-0000-0000-000000000021',gen_random_uuid(),repeat('a',40),'lesson','POST',200,10,:'a');
select public.beta_collect_request('00000000-0000-0000-0000-000000000021','10000000-0000-0000-0000-000000000023',repeat('a',40),'lesson','POST',200,10,:'a',true,false,7,5)->>'finished_at' as finished \gset
select pg_temp.assert(public.beta_collect_request('00000000-0000-0000-0000-000000000021','10000000-0000-0000-0000-000000000023',repeat('a',40),'lesson','POST',200,10,:'a',true,false,7,5)->>'finished_at'=:'finished','stable offline timestamp');
select public.beta_collect_request('00000000-0000-0000-0000-000000000021',gen_random_uuid(),repeat('a',40),'lesson','GET',200,10,p_reserve_lesson:='quiz')->>'attempt_id' as b \gset
select pg_temp.assert(:'a'<>:'b','pending A and new B stay distinct');
select pg_temp.assert(public.beta_collect_request('00000000-0000-0000-0000-000000000022',gen_random_uuid(),repeat('a',40),'lesson','POST',200,10,:'a',true,false,7,5) is null,'nonmember/other owner receives no identity');
reset role;
insert into public.lesson_completions values('00000000-0000-0000-0000-000000000021','quiz',(now() at time zone 'UTC')::date,7,6);
set local role service_role;
select public.beta_collect_request('00000000-0000-0000-0000-000000000021',gen_random_uuid(),repeat('a',40),'lesson','POST',200,10,:'b',true,true,7,6);
select pg_temp.assert((select count(*) from private.beta_attempts where projection_confirmed_at is not null and cohort='combined-fixture')=1,'B confirmation does not hide A');
reset role;
insert into public.lesson_result_events values('00000000-0000-0000-0000-000000000021',:'a','quiz');
set local role service_role;
select pg_temp.assert((private.beta_report(now()-interval '1 hour',now()+interval '1 second')->'attempts'->0->>'saved')::int=2,'late A reconciles');
select pg_temp.assert((select count(*) from private.beta_requests where cohort='combined-fixture')=6,'refresh and final retry counts exact');
select pg_temp.assert(position(:'a' in private.beta_report(now()-interval '1 hour',now()+interval '1 second')::text)=0,'no identity in aggregate');
do $$ begin
 begin
  perform public.beta_collect_request('00000000-0000-0000-0000-000000000021',gen_random_uuid(),repeat('a',40),'lesson','GET',200,-1,p_reserve_lesson:='rollback-fixture');
  raise exception 'Invalid duration must fail';
 exception when check_violation then null; end;
 if exists(select 1 from private.beta_attempts where lesson_id='rollback-fixture') then
  raise exception 'Failed observation must roll back reservation';
 end if;
end $$;
rollback;
