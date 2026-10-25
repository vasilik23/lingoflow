-- This operational migration requires Supabase's pg_cron support.
-- It never enrolls participants, enables telemetry, or deletes learning data.
create extension if not exists pg_cron;
select cron.schedule('lingoflow-beta-metrics-purge', '15 2 * * *',
  $job$set statement_timeout = '30s';
  select private.beta_purge();
  delete from cron.job_run_details
    where jobid in (select jobid from cron.job where jobname='lingoflow-beta-metrics-purge')
      and end_time < now()-interval '7 days';$job$);
