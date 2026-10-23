import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, chmod, stat, rm, symlink } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { emptyJournal, appendEvent, warningDraft, finalReview, restorePlan, runPrivateFile, runLifecycle } from './retention-lifecycle.mjs';
const OWNER='11111111-1111-4111-8111-111111111111', OTHER='22222222-2222-4222-8222-222222222222';
const NOTICE='33333333-3333-4333-8333-333333333333';
const NOW='2026-10-23T08:00:00Z', SUBMITTED='2026-09-20T08:00:00Z';
const ACTIVITY='2025-09-01T00:00:00Z';
const snapshot=(at=NOW)=>({version:1,captured_at:at,accounts:[{user_id:OWNER,created_at:'2024-01-01T00:00:00Z',last_activity_at:ACTIVITY,activity_complete:true,warning:null}],feedback:[]});
const event=(type,payload,at=SUBMITTED,n=1)=>({event_id:`00000000-0000-4000-8000-${String(n).padStart(12,'0')}`,type,at,payload});
const submitted=()=>appendEvent(emptyJournal(),event('warning_submitted',{notice_id:NOTICE,user_id:OWNER,activity_at:ACTIVITY}),NOW);
const delivered=()=>appendEvent(submitted(),event('warning_delivered',{notice_id:NOTICE,evidence_ref:'provider/delivery-verified'},SUBMITTED,2),NOW);
const checkpoint=j=>({head:j.head,confirmed_external_copy:true,storage_ref:'external/retention-copy',verified_at:NOW});
test('warning drafts in all languages require an eligible old account and send nothing',()=>{
  for(const language of ['ru','pl','en']){
    const out=warningDraft(snapshot(SUBMITTED),{user_id:OWNER,language},SUBMITTED);
    assert.equal(out.mode,'draft_only');assert.equal(out.notifications,0);
    assert(out.body.includes('https://lingoflow-learn.vercel.app/login/'));assert(out.body.includes('lingoflow.privacy@gmail.com'));
  }
  const fresh=snapshot();fresh.accounts[0].last_activity_at=NOW;
  assert.throws(()=>warningDraft(fresh,{user_id:OWNER,language:'ru'},NOW));
  const incomplete=snapshot();incomplete.accounts[0].activity_complete=false;
  assert.throws(()=>warningDraft(incomplete,{user_id:OWNER,language:'ru'},NOW));
  assert.throws(()=>warningDraft(snapshot(),{user_id:OTHER,language:'ru'},NOW));
  assert.throws(()=>warningDraft(snapshot(),{user_id:OWNER,language:'unknown'},NOW));
});
test('submission is not delivery and cannot start a deletion countdown',()=>{
  const j=submitted();const out=finalReview(snapshot(),j,checkpoint(j),NOW);
  assert.equal(out.accounts[0].action,'warning_required');assert.equal(out.remote_deletion_performed,false);
});
test('only recorded delivery enables review after 30 days and requires transactional recheck',()=>{
  const j=delivered(),out=finalReview(snapshot(),j,checkpoint(j),NOW);
  assert.equal(out.accounts[0].action,'deletion_review');assert.equal(out.requires_transactional_recheck,true);
  assert.equal(out.mutations,0);assert.equal(out.notifications,0);
});
test('30 days counted from delivery, not submission',()=>{
  const j=appendEvent(submitted(),event('warning_delivered',{notice_id:NOTICE,evidence_ref:'provider/late-delivery'},'2026-10-22T08:00:00Z',2),NOW);
  assert.equal(finalReview(snapshot(),j,checkpoint(j),NOW).accounts[0].action,'warning_wait');
});
test('bounced delivery invalidates its earlier receipt',()=>{
  const j=appendEvent(delivered(),event('warning_failed',{notice_id:NOTICE,evidence_ref:'provider/bounce'},'2026-10-22T08:00:00Z',3),NOW);
  assert.equal(finalReview(snapshot(),j,checkpoint(j),NOW).accounts[0].action,'warning_required');
  assert.throws(()=>appendEvent(j,event('warning_delivered',{notice_id:NOTICE,evidence_ref:'provider/again'},NOW,4),NOW));
});
test('fresh activity and changed activity baseline prevent old warning reuse',()=>{
  const j=delivered(),fresh=snapshot();fresh.accounts[0].last_activity_at=NOW;
  assert.equal(finalReview(fresh,j,checkpoint(j),NOW).accounts[0].action,'active');
  fresh.accounts[0].last_activity_at='2025-09-02T00:00:00Z';
  assert.equal(finalReview(fresh,j,checkpoint(j),NOW).accounts[0].action,'warning_required');
});
test('snapshot cannot forge delivery; incomplete history never authorises inactivity',()=>{
  const s=snapshot(),j=emptyJournal();s.accounts[0].warning={delivered_at:SUBMITTED,activity_at_delivery:ACTIVITY};
  assert.equal(finalReview(s,j,checkpoint(j),NOW).accounts[0].action,'warning_required');
  const deliveredJournal=delivered();s.accounts[0].activity_complete=false;
  assert.equal(finalReview(s,deliveredJournal,checkpoint(deliveredJournal),NOW).accounts[0].action,'manual_review');
});
test('final check refuses stale snapshots and missing/old/wrong external checkpoints',()=>{
  const j=delivered(),s=snapshot('2026-10-23T07:54:59Z');
  assert.throws(()=>finalReview(s,j,checkpoint(j),NOW));
  for(const cp of [null,{...checkpoint(j),head:'wrong'},{...checkpoint(j),confirmed_external_copy:false},{...checkpoint(j),verified_at:'2026-10-21T08:00:00Z'}])assert.throws(()=>finalReview(snapshot(),j,cp,NOW));
});
test('reopened feedback is kept at the final review; missing closure never expires',()=>{
  const j=emptyJournal(),s=snapshot();s.feedback=[{id:OTHER,status:'reviewed',created_at:'2024-01-01T00:00:00Z',closed_at:null}];
  assert.equal(finalReview(s,j,checkpoint(j),NOW).feedback[0].action,'keep');
  s.feedback[0].status='resolved';assert.equal(finalReview(s,j,checkpoint(j),NOW).feedback[0].action,'manual_review');
});
test('journal retries are idempotent; reused IDs with changed data are rejected',()=>{
  const e=event('warning_submitted',{notice_id:NOTICE,user_id:OWNER,activity_at:ACTIVITY}),j=appendEvent(emptyJournal(),e,NOW);
  assert.equal(appendEvent(j,e,NOW),j);
  assert.throws(()=>appendEvent(j,{...e,payload:{...e.payload,user_id:OTHER}},NOW));
});
test('corruption, truncation and reordering do not pass a checkpoint',()=>{
  for(const mutate of [j=>j.entries[0].payload.user_id=OTHER,j=>j.entries.reverse(),j=>j.entries.pop()]){
    const j=structuredClone(delivered());mutate(j);assert.throws(()=>restorePlan(j,checkpoint(j),NOW));
  }
});
test('unknown events, missing evidence, future timestamps and extra personal fields rejected',()=>{
  const inputs=[event('unknown',{}),event('warning_delivered',{notice_id:NOTICE,evidence_ref:'proof'}),event('account_deleted',{target_id:OWNER,evidence_ref:''}),event('account_deleted',{target_id:OWNER,evidence_ref:'support/private@example.com'}),event('account_deleted',{target_id:OWNER,evidence_ref:'proof',email:'private@example.com'}),event('account_deleted',{target_id:OWNER,evidence_ref:'proof'},'2027-01-01T00:00:00Z')];
  for(const e of inputs)assert.throws(()=>appendEvent(emptyJournal(),e,NOW));
});
test('restore plan deduplicates confirmed removals but never opens access or performs writes',()=>{
  let j=emptyJournal();j=appendEvent(j,event('account_deleted',{target_id:OWNER,evidence_ref:'auth/deletion-1'},NOW,1),NOW);
  j=appendEvent(j,event('account_deleted',{target_id:OWNER,evidence_ref:'auth/deletion-1-retry'},NOW,2),NOW);
  j=appendEvent(j,event('feedback_deleted',{target_id:OTHER,evidence_ref:'db/deletion-2'},NOW,3),NOW);
  const out=restorePlan(j,checkpoint(j),NOW);
  assert.deepEqual(out.account_ids,[OWNER]);assert.deepEqual(out.feedback_ids,[OTHER]);
  assert.equal(out.enable_public_access,false);assert.equal(out.requires_post_checkpoint_reconciliation,true);assert.equal(out.mutations,0);
});
test('closed lifecycle from draft to restore remains an operator dry run',()=>{
  const draft=warningDraft(snapshot(SUBMITTED),{user_id:OWNER,language:'en'},SUBMITTED);assert.equal(draft.notifications,0);
  let j=delivered();const review=finalReview(snapshot(),j,checkpoint(j),NOW);assert.equal(review.accounts[0].action,'deletion_review');
  j=appendEvent(j,event('account_deleted',{target_id:OWNER,evidence_ref:'auth/verified-absent'},NOW,3),NOW);
  assert.deepEqual(restorePlan(j,checkpoint(j),NOW).account_ids,[OWNER]);
  assert.equal(runLifecycle({action:'restore',journal:j,checkpoint:checkpoint(j)},NOW).mode,'restore_plan_only');
});
test('private CLI path writes exclusive 0600 output and prints no identities',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'lf-retention-cycle-'));await chmod(dir,0o700);
  try{
    const input=join(dir,'input.json'),output=join(dir,'output.json'),j=delivered();
    await writeFile(input,JSON.stringify({action:'final-review',snapshot:snapshot(),journal:j,checkpoint:checkpoint(j)}),{mode:0o600});
    const summary=await runPrivateFile(input,output,NOW);assert(!JSON.stringify(summary).includes(OWNER));
    assert.equal((await stat(output)).mode&0o777,0o600);assert.equal(JSON.parse(await readFile(output)).mode,'operator_final_review_only');
    await assert.rejects(runPrivateFile(input,output,NOW));
    await symlink(input,join(dir,'linked.json'));await assert.rejects(runPrivateFile(join(dir,'linked.json'),join(dir,'other.json'),NOW));
    await chmod(input,0o644);await assert.rejects(runPrivateFile(input,join(dir,'other.json'),NOW));
  }finally{await rm(dir,{recursive:true,force:true});}
});
test('previously confirmed deleted data reappearing blocks final review',()=>{
  const j=appendEvent(emptyJournal(),event('account_deleted',{target_id:OWNER,evidence_ref:'auth/previous-deletion'},NOW,1),NOW);
  assert.throws(()=>finalReview(snapshot(),j,checkpoint(j),NOW));
  const s=snapshot();s.feedback=[{id:OTHER,status:'new',created_at:NOW,closed_at:null}];
  const feedbackJournal=appendEvent(emptyJournal(),event('feedback_deleted',{target_id:OTHER,evidence_ref:'db/previous-deletion'},NOW,1),NOW);
  assert.throws(()=>finalReview(s,feedbackJournal,checkpoint(feedbackJournal),NOW));
});
