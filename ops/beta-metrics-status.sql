-- Trusted operator only. Aggregate output; no participant IDs or credentials.
select jsonb_build_object(
 'collection_members',(select count(*) from private.beta_members),
 'cleanup_job_active',(select active from cron.job where jobname='lingoflow-beta-metrics-purge'),
 'cleanup_schedule',(select schedule from cron.job where jobname='lingoflow-beta-metrics-purge'),
 'last_cleanup',(select jsonb_build_object('status',r.status,'ended_at',r.end_time)
   from cron.job_run_details r join cron.job j using(jobid)
   where j.jobname='lingoflow-beta-metrics-purge' order by r.runid desc limit 1),
 'cleanup_healthy',exists(select 1 from cron.job j
   where j.jobname='lingoflow-beta-metrics-purge' and j.active and j.schedule='15 2 * * *'
     and (select r.status='succeeded' and r.end_time>=now()-interval '26 hours'
          from cron.job_run_details r where r.jobid=j.jobid order by r.runid desc limit 1)),
 'requests_over_30_days',(select count(*) from private.beta_requests where observed_at<now()-interval '30 days'),
 'attempts_over_30_days',(select count(*) from private.beta_attempts where reserved_at<now()-interval '30 days')
) as beta_metrics_status;
