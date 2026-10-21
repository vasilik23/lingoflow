-- Run as the database operator. Every fixture is rolled back, including Auth rows.
begin;
insert into auth.users(id, email) values
 ('c47c7a48-c009-43c9-9709-63b5c56edc11', 'b2-rls-a@example.invalid'),
 ('c47c7a48-c009-43c9-9709-63b5c56edc22', 'b2-rls-b@example.invalid');
set local role authenticated;
select set_config('request.jwt.claim.sub','c47c7a48-c009-43c9-9709-63b5c56edc11', true);
insert into public.b2_listening_attempts(user_id,attempt_id,material_id,content_version,correct,missed_mask)
values ('c47c7a48-c009-43c9-9709-63b5c56edc11','4b73dbe2-45db-445e-adb5-68270cb17351','hybrid-work-message',1,2,2);
-- The same retry has one result, even with no update grant.
insert into public.b2_listening_attempts(user_id,attempt_id,material_id,content_version,correct,missed_mask)
values ('c47c7a48-c009-43c9-9709-63b5c56edc11','4b73dbe2-45db-445e-adb5-68270cb17351','hybrid-work-message',1,2,2)
on conflict(user_id,attempt_id) do nothing;
do $$ begin
 if (select count(*) from public.b2_listening_attempts) <> 1 then raise exception 'Owner read or duplicate failed'; end if;
 begin
   insert into public.b2_listening_attempts(user_id,attempt_id,material_id,content_version,correct,missed_mask)
   values ('c47c7a48-c009-43c9-9709-63b5c56edc22',gen_random_uuid(),'hybrid-work-message',1,3,0);
   raise exception 'Foreign insert allowed';
 exception when insufficient_privilege then null; end;
 begin
   update public.b2_listening_attempts set correct=3,missed_mask=0;
   raise exception 'Update allowed';
 exception when insufficient_privilege then null; end;
 begin
   delete from public.b2_listening_attempts;
   raise exception 'Delete allowed';
 exception when insufficient_privilege then null; end;
 begin
   insert into public.b2_listening_attempts(user_id,attempt_id,material_id,content_version,correct,missed_mask,completed_at)
   values ('c47c7a48-c009-43c9-9709-63b5c56edc11',gen_random_uuid(),'hybrid-work-message',1,3,0,now()-interval '2 days');
   raise exception 'Client date override allowed';
 exception when insufficient_privilege then null; end;
 begin
   insert into public.b2_listening_attempts(user_id,attempt_id,material_id,content_version,correct,missed_mask)
   values ('c47c7a48-c009-43c9-9709-63b5c56edc11',gen_random_uuid(),'hybrid-work-message',1,3,1);
   raise exception 'Invalid score accepted';
 exception when check_violation then null; end;
end $$;
select set_config('request.jwt.claim.sub','c47c7a48-c009-43c9-9709-63b5c56edc22',true);
do $$ begin
 if (select count(*) from public.b2_listening_attempts) <> 0 then raise exception 'Foreign result exposed'; end if;
end $$;
set local role anon;
do $$ begin
 begin
   perform * from public.b2_listening_attempts;
   raise exception 'Anon read allowed';
 exception when insufficient_privilege then null; end;
 begin
   insert into public.b2_listening_attempts(user_id,attempt_id,material_id,content_version,correct,missed_mask)
   values ('c47c7a48-c009-43c9-9709-63b5c56edc11',gen_random_uuid(),'hybrid-work-message',1,3,0);
   raise exception 'Anon write allowed';
 exception when insufficient_privilege then null; end;
end $$;
reset role;
delete from auth.users where id='c47c7a48-c009-43c9-9709-63b5c56edc11';
do $$ begin
 if exists(select 1 from public.b2_listening_attempts where user_id='c47c7a48-c009-43c9-9709-63b5c56edc11') then raise exception 'Account deletion did not cascade'; end if;
end $$;
rollback;
