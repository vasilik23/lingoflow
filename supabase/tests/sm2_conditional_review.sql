-- Existing schema only. Fixtures and every schedule change are rolled back.
begin;
insert into auth.users(id,email) values
 ('88ce7df4-211a-4da5-b9f7-ab39f4dc7801','sm2-cas-a@example.invalid'),
 ('88ce7df4-211a-4da5-b9f7-ab39f4dc7802','sm2-cas-b@example.invalid');
insert into public.personal_words(id,user_id,word,translation) values
 ('eaf9a39d-490c-4b29-9270-22f893bf8ad1','88ce7df4-211a-4da5-b9f7-ab39f4dc7801','CAS fixture','fixture');
set local role authenticated;
select set_config('request.jwt.claim.sub','88ce7df4-211a-4da5-b9f7-ab39f4dc7801',true);
do $$ declare affected integer; begin
 update public.personal_words set repetitions=1,interval_days=1,last_reviewed_at='2026-10-21T12:00:00Z'
 where id='eaf9a39d-490c-4b29-9270-22f893bf8ad1' and user_id='88ce7df4-211a-4da5-b9f7-ab39f4dc7801' and last_reviewed_at is null;
 get diagnostics affected=row_count;
 if affected <> 1 then raise exception 'Initial conditional save failed'; end if;
 -- A lost ACK or competing request still carries the old NULL snapshot.
 update public.personal_words set repetitions=2,last_reviewed_at='2026-10-21T12:00:01Z'
 where id='eaf9a39d-490c-4b29-9270-22f893bf8ad1' and user_id='88ce7df4-211a-4da5-b9f7-ab39f4dc7801' and last_reviewed_at is null;
 get diagnostics affected=row_count;
 if affected <> 0 then raise exception 'Stale NULL snapshot advanced twice'; end if;
 update public.personal_words set repetitions=2,last_reviewed_at='2026-10-22T12:00:00Z'
 where id='eaf9a39d-490c-4b29-9270-22f893bf8ad1' and user_id='88ce7df4-211a-4da5-b9f7-ab39f4dc7801' and last_reviewed_at='2026-10-21T14:00:00+02:00';
 get diagnostics affected=row_count;
 if affected <> 1 then raise exception 'Timestamp snapshot did not normalize timezone'; end if;
 update public.personal_words set repetitions=3,last_reviewed_at='2026-10-22T12:00:01Z'
 where id='eaf9a39d-490c-4b29-9270-22f893bf8ad1' and user_id='88ce7df4-211a-4da5-b9f7-ab39f4dc7801' and last_reviewed_at='2026-10-21T12:00:00Z';
 get diagnostics affected=row_count;
 if affected <> 0 then raise exception 'Stale timestamp advanced twice'; end if;
 if (select repetitions from public.personal_words where id='eaf9a39d-490c-4b29-9270-22f893bf8ad1') <> 2 then raise exception 'Wrong final repetitions'; end if;
end $$;
select set_config('request.jwt.claim.sub','88ce7df4-211a-4da5-b9f7-ab39f4dc7802',true);
do $$ declare affected integer; begin
 update public.personal_words set repetitions=99 where id='eaf9a39d-490c-4b29-9270-22f893bf8ad1' and last_reviewed_at='2026-10-22T12:00:00Z';
 get diagnostics affected=row_count;
 if affected <> 0 then raise exception 'Foreign owner modified schedule'; end if;
 if exists(select 1 from public.personal_words where id='eaf9a39d-490c-4b29-9270-22f893bf8ad1') then raise exception 'Foreign word exposed'; end if;
end $$;
rollback;
