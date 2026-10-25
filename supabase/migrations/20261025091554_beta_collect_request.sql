-- Additive service-only endpoint; old RPCs remain for compatible rollback.
-- One transaction reserves/finalizes an attempt AND records the request.
create function public.beta_collect_request(
 p_owner uuid,p_request uuid,p_release text,p_route text,p_method text,
 p_status integer,p_duration integer,p_attempt uuid default null,
 p_finished boolean default false,p_saved boolean default false,
 p_total integer default null,p_known integer default null,p_reserve_lesson text default null
) returns jsonb language plpgsql security invoker set search_path=pg_catalog as $$
declare member private.beta_members; effective uuid; finished timestamptz;
begin
 select * into member from private.beta_members where user_id=p_owner
   and enrolled_at<=now() and expires_at>now();
 if not found then return null; end if;
 if p_route='lesson' and p_method='GET' and p_status=200 and p_reserve_lesson is not null then
   effective := public.beta_reserve_attempt(p_owner,p_reserve_lesson,p_release);
 elsif p_route='lesson' and p_method='POST' and p_status=200 then
   select attempt_id into effective from private.beta_attempts
     where attempt_id=p_attempt and user_id=p_owner and cohort=member.cohort
       and release_sha=p_release and reserved_at>=now()-interval '30 days';
   if effective is not null and p_finished then
     finished := public.beta_finish_attempt(p_owner,effective,p_release);
   end if;
 end if;
 perform public.beta_observe_request(p_owner,p_request,p_release,p_route,p_method,
   p_status,p_duration,effective,p_finished,p_saved,p_total,p_known);
 return jsonb_build_object('attempt_id',effective,'finished_at',finished);
end $$;
revoke all on function public.beta_collect_request(uuid,uuid,text,text,text,integer,integer,uuid,boolean,boolean,integer,integer,text) from public,anon,authenticated;
grant execute on function public.beta_collect_request(uuid,uuid,text,text,text,integer,integer,uuid,boolean,boolean,integer,integer,text) to service_role;
