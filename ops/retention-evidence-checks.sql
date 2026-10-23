-- Transactional operator checks: all fixture writes roll back. No emails or external jobs.
begin;
do $$
declare owner_id uuid; other_id uuid; feedback_id uuid := gen_random_uuid(); stamp timestamptz; original_stamp timestamptz; started timestamptz; ttl integer; payload jsonb;
begin
  select id into owner_id from public.profiles order by created_at, id limit 1;
  select id into other_id from public.profiles where id<>owner_id order by created_at,id limit 1;
  if owner_id is null or other_id is null then raise exception 'two_existing_fixture_owners_required'; end if;
  if has_table_privilege('anon','public.profiles','TRUNCATE') or has_table_privilege('authenticated','public.profiles','TRUNCATE') then raise exception 'truncate_still_granted'; end if;
  if has_function_privilege('anon','public.record_account_activity()','EXECUTE') then raise exception 'anon_rpc_still_granted'; end if;
  if has_function_privilege('authenticated','private.retention_review_snapshot()','EXECUTE') then raise exception 'learner_can_read_inventory'; end if;
  perform set_config('request.jwt.claims',json_build_object('sub',owner_id,'role','authenticated')::text,true);
  set local role authenticated;
  ttl := public.record_account_activity();
  if ttl < 1 or ttl > 900 then raise exception 'rpc_ack_out_of_range'; end if;
  select last_request_at, activity_tracking_started_at into stamp,started from public.profiles where id=owner_id;
  if stamp is null or started is null then raise exception 'activity_not_stamped'; end if;
  original_stamp := stamp;
  perform public.record_account_activity();
  select last_request_at into stamp from public.profiles where id=owner_id;
  if stamp is distinct from original_stamp then raise exception 'second_request_not_throttled'; end if;
  if exists(select 1 from public.profiles where id=other_id) then raise exception 'cross_owner_profile_visible'; end if;
  update public.profiles set last_request_at='2099-01-01',activity_tracking_started_at='1900-01-01' where id=owner_id;
  select last_request_at,activity_tracking_started_at into stamp,original_stamp from public.profiles where id=owner_id;
  if stamp>clock_timestamp()+interval '2 seconds' or original_stamp is distinct from started then raise exception 'client_forged_activity'; end if;
  update public.profiles set last_request_at='2099-01-01' where id=other_id;
  if found then raise exception 'cross_owner_write_allowed'; end if;
  insert into public.user_feedback(id,user_id,category,message,status,closed_at) values(feedback_id,owner_id,'technical','Synthetic transactional retention check.','new','2000-01-01');
  if exists(select 1 from public.user_feedback where id=feedback_id and closed_at is not null) then raise exception 'client_forged_closure'; end if;
  begin
    update public.user_feedback set status='resolved' where id=feedback_id;
    raise exception 'learner_can_close_feedback';
  exception when insufficient_privilege then null;
  end;
  reset role;
  update public.user_feedback set status='resolved' where id=feedback_id;
  select closed_at into stamp from public.user_feedback where id=feedback_id;
  if stamp is null or stamp<clock_timestamp()-interval '10 seconds' then raise exception 'resolution_not_stamped'; end if;
  update public.user_feedback set message='Synthetic update without reopening.' where id=feedback_id;
  select closed_at into original_stamp from public.user_feedback where id=feedback_id;
  if stamp is distinct from original_stamp then raise exception 'resolved_edit_reset_closure'; end if;
  update public.user_feedback set status='reviewed' where id=feedback_id;
  if exists(select 1 from public.user_feedback where id=feedback_id and closed_at is not null) then raise exception 'reopen_did_not_clear_closure'; end if;
  update public.user_feedback set status='resolved' where id=feedback_id;
  select closed_at into original_stamp from public.user_feedback where id=feedback_id;
  if original_stamp<stamp then raise exception 'reclose_not_monotonic'; end if;
  payload:=private.retention_review_snapshot();
  if payload->>'version'<>'1' or jsonb_array_length(payload->'accounts')<2 then raise exception 'inventory_incomplete'; end if;
  if payload::text ~ 'Synthetic|@|password|access_token' then raise exception 'inventory_contains_personal_text'; end if;
end;
$$;

rollback;
