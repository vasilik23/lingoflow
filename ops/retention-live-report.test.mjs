import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, stat, chmod, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { snapshotFromResult, writeLiveReport } from './retention-live-report.mjs';
const id='11111111-1111-4111-8111-111111111111';
const result=()=>[{retention_snapshot:{version:1,captured_at:new Date().toISOString(),accounts:[{user_id:id,created_at:'2026-01-01T00:00:00Z',last_activity_at:'2026-01-01T00:00:00Z',activity_complete:false,email:'private@example.invalid'}],feedback:[]}}];
test('single SQL column is required; arbitrary result and errors do not become snapshots',()=>{
  for(const input of [null,[],[{},{}],[{error:'secret'}],{accounts:[]}]) assert.throws(()=>snapshotFromResult(input));
});
test('private source text is discarded; coverage remains conservative',()=>{
  const snapshot=snapshotFromResult(result());
  assert.equal(snapshot.accounts[0].activity_complete,false);
  assert(!JSON.stringify(snapshot).includes('private@example.invalid'));
});
test('live report writes only private exclusive files and prints aggregate summary',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'lf-live-retention-'));
  try{
    await chmod(dir,0o700);
    const summary=await writeLiveReport(result(),dir);
    assert(!JSON.stringify(summary).includes(id));
    for(const file of ['snapshot.json','report.json']) assert.equal((await stat(join(dir,file))).mode&0o777,0o600);
    assert(!String(await readFile(join(dir,'snapshot.json'))).includes('private@example.invalid'));
    await assert.rejects(writeLiveReport(result(),dir));
  }finally{await rm(dir,{recursive:true,force:true});}
});
test('shared directories and stale input are rejected before writing',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'lf-live-retention-'));
  try{
    await chmod(dir,0o755);
    await assert.rejects(writeLiveReport(result(),dir));
    const old=result();old[0].retention_snapshot.captured_at='2000-01-01T00:00:00Z';
    assert.throws(()=>snapshotFromResult(old));
  }finally{await rm(dir,{recursive:true,force:true});}
});
