-- Rollback-only verification; creates isolated temporary Auth owners.
begin;
select set_config('lf.owner_one',gen_random_uuid()::text,true),
       set_config('lf.owner_two',gen_random_uuid()::text,true),
       set_config('lf.run',gen_random_uuid()::text,true),
       set_config('lf.results','[{"id":"listening","status":"scored","correct":2,"total":5,"incorrect":1,"unanswered":2,"timed_out":true},{"id":"reading","status":"skipped","timed_out":false},{"id":"grammar","status":"skipped","timed_out":null},{"id":"writing","status":"self_review","timed_out":false},{"id":"speaking","status":"self_review","timed_out":true}]',true);
insert into auth.users(id,email) values
  (current_setting('lf.owner_one')::uuid,current_setting('lf.owner_one')||'@fixture.invalid'),
  (current_setting('lf.owner_two')::uuid,current_setting('lf.owner_two')||'@fixture.invalid');
select set_config('request.jwt.claim.sub',current_setting('lf.owner_one'),true);
set local role authenticated;
insert into public.b1_run_attempts(user_id,run_id,variant_id,content_version,started_at,finished_at,results)
values(auth.uid(),current_setting('lf.run')::uuid,'b1-weekly-v1',9,now()-interval '10 minutes',now(),current_setting('lf.results')::jsonb);
insert into public.b1_run_attempts(user_id,run_id,variant_id,content_version,started_at,finished_at,results)
values(auth.uid(),current_setting('lf.run')::uuid,'b1-weekly-v1',9,now()-interval '10 minutes',now(),current_setting('lf.results')::jsonb)
on conflict(user_id,run_id) do nothing;
do $$ begin
  if (select count(*) from public.b1_run_attempts) <> 1 then raise exception 'Own read/idempotence failed'; end if;
  if has_table_privilege('authenticated','public.b1_run_attempts','UPDATE') or has_table_privilege('authenticated','public.b1_run_attempts','DELETE') then raise exception 'Immutable grants failed'; end if;
  begin
    insert into public.b1_run_attempts(user_id,run_id,variant_id,content_version,started_at,finished_at,results)
    values(current_setting('lf.owner_two')::uuid,gen_random_uuid(),'b1-weekly-v1',9,now(),now(),current_setting('lf.results')::jsonb);
    raise exception 'Foreign insert incorrectly allowed';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.b1_run_attempts(user_id,run_id,variant_id,content_version,started_at,finished_at,results)
    values(auth.uid(),gen_random_uuid(),'b1-weekly-v1',9,now(),now(),jsonb_set(current_setting('lf.results')::jsonb,'{0,essay}','"private draft"'::jsonb));
    raise exception 'Free text incorrectly allowed';
  exception when check_violation then null; end;
  if public.valid_b1_run_results('null'::jsonb) or public.valid_b1_run_results('[]'::jsonb) or public.valid_b1_run_results('[1,2,3,4,5]'::jsonb) then raise exception 'Invalid shape accepted'; end if;
end $$;
select set_config('request.jwt.claim.sub',current_setting('lf.owner_two'),true);
do $$ begin
  if (select count(*) from public.b1_run_attempts) <> 0 then raise exception 'Foreign read allowed'; end if;
end $$;
set local role anon;
do $$ begin
  begin perform count(*) from public.b1_run_attempts; raise exception 'Anonymous read allowed';
  exception when insufficient_privilege then null; end;
  if has_table_privilege('anon','public.b1_run_attempts','INSERT') then raise exception 'Anonymous insert allowed'; end if;
end $$;
reset role;
delete from auth.users where id=current_setting('lf.owner_one')::uuid;
do $$ begin
  if exists(select 1 from public.b1_run_attempts where user_id=current_setting('lf.owner_one')::uuid) then raise exception 'Cascade failed'; end if;
end $$;
rollback;
