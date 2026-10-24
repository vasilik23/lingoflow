import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, chmod, stat, readFile, rm, symlink} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {appDuration, percentile, summarize, probe, writeReport, ORIGIN} from './performance-probe.mjs';
const commit = 'a'.repeat(40);
const sample = (run=1, overrides={}) => ({route:'today',run,status:200,headers_ms:10,total_ms:15,app_ms:2,error:null,...overrides});
const evidence = samples => ({version:1,commit,context:'authenticated',samples});

test('nearest rank p95 is computed from all samples, rounded upward, without mutation',()=>{
  const values=[100.2,...Array(19).fill(1.1)];
  assert.equal(percentile(values,.95),2);
  assert.equal(percentile(values,.5),2);
  assert.equal(values[0],100.2);
  assert.equal(percentile([1,99],.95),99);
  for(const input of [[],[NaN],[-1],[Infinity]])assert.throws(()=>percentile(input,.95));
});
test('server timing accepts one app metric only; missing/malformed is unknown, not zero',()=>{
  assert.equal(appDuration('db;dur=2, app;dur=123.5'),123.5);
  assert.equal(appDuration('app;dur=0'),0);
  for(const value of [null,'','app;dur=-1','app;dur=NaN','app;dur=1, app;dur=2','app;dur=1junk'])assert.equal(appDuration(value),null);
});
test('first and subsequent samples are separated without claiming cold/warm instances',()=>{
  const report=summarize(evidence([sample(3,{headers_ms:20,total_ms:21}),sample(),sample(2,{headers_ms:30,total_ms:35,app_ms:null})]));
  const route=report.routes[0];
  assert.equal(route.first.headers.p50_ms,10);
  assert.equal(route.subsequent.headers.p95_ms,30);
  assert.equal(route.subsequent.app.count,1);
  assert.equal(report.beta_readiness_evidence,false);
  assert.equal(report.field_metrics,false);
});
test('failed HTTP, redirects and transport errors stay visible; zero success latency is unknown',()=>{
  const samples=[sample(1,{status:302}),sample(2,{status:500}),sample(3,{status:403}),
    sample(4,{status:null,headers_ms:null,total_ms:null,app_ms:null,error:'transport'})];
  const all=summarize(evidence(samples)).routes[0].all;
  assert.equal(all.attempts,4); assert.equal(all.http_responses,3);
  assert.equal(all.redirects,1);assert.equal(all.server_errors,1);assert.equal(all.client_errors,1);
  assert.equal(all.transport_errors,1);assert.equal(all.headers,null);assert.equal(all.app,null);
});
test('invalid evidence and arbitrary private fields fail instead of leaking into aggregates',()=>{
  const valid=evidence([sample()]);
  for(const bad of [{...valid,email:'private@example.invalid'},{...valid,commit:'main'},{...valid,commit:[commit]},
    {...valid,context:'cohort'},{...valid,samples:[]},evidence([sample(2)]),evidence([sample(),sample()]),
    evidence([sample(1,{url:'https://private.invalid'})]),evidence([sample(1,{headers_ms:NaN})]),
    evidence([sample(1,{app_ms:-1})]),evidence([sample(1,{status:null})]),
    {...valid,context:'public'},evidence([sample(1,{error:'private exception'})])])assert.throws(()=>summarize(bad));
});
test('probe uses a bounded, sequential, canonical GET allowlist and never follows redirects',async()=>{
  let active=0,maximum=0;const calls=[];
  const result=await probe({commit,runs:2,fetcher:async(url,options)=>{
    active++;maximum=Math.max(maximum,active);calls.push([url,options]);
    await new Promise(resolve=>setTimeout(resolve,1));active--;
    return new Response('private body',{status:200,headers:{'Server-Timing':'app;dur=7','set-cookie':'secret','X-Request-ID':'private'}});
  }});
  assert.equal(calls.length,6);assert.equal(maximum,1);
  assert(Date.parse(result.report.finished_at)>=Date.parse(result.report.started_at));
  assert.deepEqual([...new Set(calls.map(x=>x[0]))],[ORIGIN+'/start/',ORIGIN+'/login/',ORIGIN+'/sources/']);
  for(const [,options]of calls){assert.equal(options.method,'GET');assert.equal(options.redirect,'manual');assert(!('cookie'in options.headers));}
  assert(!JSON.stringify(result).includes('private'));assert(!JSON.stringify(result).includes('secret'));
  assert.equal(result.report.routes[0].all.app.p95_ms,7);
});
test('transport exceptions are redacted, never retried or reported as zero latency',async()=>{
  let calls=0;const {report}=await probe({commit,runs:2,fetcher:async()=>{calls++;throw Error('token-private');}});
  assert.equal(calls,6);assert.equal(report.routes[0].all.transport_errors,2);
  assert.equal(report.routes[0].all.total,null);assert(!JSON.stringify(report).includes('token-private'));
});
test('invalid probe parameters issue no requests',async()=>{
  let calls=0;const fetcher=async()=>{calls++;};
  for(const options of [{commit:'main'},{commit:[commit]},{runs:1},{runs:11},{context:'private'}])await assert.rejects(probe({commit,fetcher,...options}));
  assert.equal(calls,0);
});
test('oversized or interrupted body is not a successful page sample',async()=>{
  const {report}=await probe({commit,runs:2,fetcher:async()=>new Response(new Uint8Array(5*1024*1024+1),{status:200})});
  for(const r of report.routes){assert.equal(r.all.successful,0);assert.equal(r.all.transport_errors,2);assert.equal(r.all.total,null);}
});
test('report is private, exclusive and cannot overwrite a symlink or use shared parent',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'lf-performance-'));const report=summarize(evidence([sample()]));
  try{
    await chmod(dir,0o700);const output=join(dir,'report.json');
    await writeReport(output,report);assert.equal((await stat(output)).mode&0o777,0o600);
    assert.equal(JSON.parse(await readFile(output)).commit,commit);
    await assert.rejects(writeReport(output,report));
    await symlink(output,join(dir,'link.json'));await assert.rejects(writeReport(join(dir,'link.json'),report));
    await chmod(dir,0o755);await assert.rejects(writeReport(join(dir,'other.json'),report));
  }finally{await rm(dir,{recursive:true,force:true});}
});
