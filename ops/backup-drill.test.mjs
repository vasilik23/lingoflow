import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, chmod, readFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { seal, verify, restoreLocal, restoreConfig } from './backup-drill.mjs';

async function fixture(t) {
  const dir = await mkdtemp(join(tmpdir(), 'lf-backup-test-'));
  await chmod(dir, 0o700);
  t.after(() => rm(dir, { recursive: true, force: true }));
  for (const name of ['roles.sql','schema.sql','data.sql']) await writeFile(join(dir,name), '-- synthetic test SQL\n', { mode: 0o600 });
  return dir;
}
test('seals three private files; refuses overwrite; verifies without connecting', async t => {
  const d = await fixture(t);
  assert.equal((await seal(d)).restored, false);
  assert.equal((await verify(d)).status, 'verified');
  await assert.rejects(seal(d));
  const manifest = JSON.parse(await readFile(join(d,'manifest.json')));
  assert.deepEqual(Object.keys(manifest.files).sort(), ['data.sql','roles.sql','schema.sql']);
});
test('tampered archive prevents any target connection', async t => {
  const d = await fixture(t); await seal(d);
  await writeFile(join(d,'data.sql'), 'changed');
  let called = false;
  await assert.rejects(restoreLocal(d, '54322', 'secret', true, () => { called = true; }), /archive_integrity_failed/);
  assert.equal(called, false);
});
test('rejects symlinks, shared permissions and missing files', async t => {
  const d = await fixture(t);
  await chmod(join(d,'data.sql'), 0o644);
  await assert.rejects(seal(d), /private_regular_file_required/);
  await rm(join(d,'data.sql')); await symlink(join(d,'roles.sql'), join(d,'data.sql'));
  await assert.rejects(seal(d), /private_regular_file_required/);
  await rm(join(d,'data.sql')); await assert.rejects(seal(d));
});
test('requires explicit execution and local numeric port; does not inherit PG overrides', async t => {
  const d = await fixture(t); await seal(d);
  for (const p of ['5432 host=example.com', 'https://example.com', '54322?host=example.com', '0', '65536']) assert.throws(() => restoreConfig(p, 'secret'));
  assert.throws(() => restoreConfig('54322', ''));
  await assert.rejects(restoreLocal(d, '54322', 'secret', false), /explicit_execute_required/);
  const c = restoreConfig('54322', 'secret');
  assert.ok(c.args.includes('--host=127.0.0.1'));
  assert.deepEqual(Object.keys(c.env).sort(), ['PATH','PGCONNECT_TIMEOUT','PGPASSFILE','PGPASSWORD']);
  assert.equal(c.args.some(x=>x.includes('secret')), false);
});
test('nonempty or inaccessible local target never starts import', async t => {
  const d = await fixture(t); await seal(d);
  let calls = 0;
  await assert.rejects(restoreLocal(d,'54322','secret',true,()=>{calls++;return {status:0,stdout:'f\n'}}), /empty_local_supabase_required/);
  assert.equal(calls,1);
  await assert.rejects(restoreLocal(d,'54322','secret',true,()=>({status:1,stderr:'sensitive'})), /local_psql_failed/);
});
test('imports in one transaction with stop-on-error; reports pending acceptance', async t => {
  const d = await fixture(t); await seal(d); const calls=[];
  const result=await restoreLocal(d,'54322','secret',true,(exe,args,options)=>{
    calls.push({exe,args,options}); return {status:0,stdout:'t\n'};
  });
  assert.equal(calls.length,2);
  assert.ok(calls[1].args.includes('--single-transaction'));
  assert.ok(calls[1].args.includes('--variable=ON_ERROR_STOP=1'));
  assert.equal(result.acceptance_required,true);
  await assert.rejects(restoreLocal(d,'54322','secret',true,(_exe,args)=>({status:args.includes('--single-transaction')?1:0,stdout:'t\n'})), /local_psql_failed/);
});
test('malformed or wrong-project manifest cannot be verified', async t => {
  const d = await fixture(t); await seal(d);
  const f=join(d,'manifest.json'),m=JSON.parse(await readFile(f));m.project='wrong';
  await writeFile(f,JSON.stringify(m));await assert.rejects(verify(d),/invalid_manifest/);
  await writeFile(f,'{bad');await assert.rejects(verify(d),/invalid_manifest/);
});
test('CLI errors never print paths, SQL or supplied secret', () => {
  const r=spawnSync(process.execPath,['ops/backup-drill.mjs','restore-local','/private/secret-location','--port','example.com','--execute'],{encoding:'utf8',env:{PATH:process.env.PATH,LINGOFLOW_RESTORE_PASSWORD:'sensitive-password'}});
  assert.equal(r.status,2);assert.equal(r.stderr.includes('sensitive-password'),false);assert.equal(r.stderr.includes('secret-location'),false);
  assert.equal(JSON.parse(r.stderr).code,'explicit_local_port_required');
});
test('archives in the repository or a shared directory cannot be sealed', async t => {
  const inside=await mkdtemp(join(process.cwd(),'.backup-test-'));
  t.after(()=>rm(inside,{recursive:true,force:true}));
  await chmod(inside,0o700);
  await assert.rejects(seal(inside),/archive_must_be_outside_repository/);
  const d=await fixture(t);await chmod(d,0o755);
  await assert.rejects(seal(d),/private_directory_required/);
});
test('oversized manifest and extra filenames are rejected before connecting', async t => {
  const d=await fixture(t);await seal(d);const f=join(d,'manifest.json');
  const m=JSON.parse(await readFile(f));m.files['../other.sql']=m.files['data.sql'];
  await writeFile(f,JSON.stringify(m));await assert.rejects(verify(d),/invalid_manifest/);
  await writeFile(f,' '.repeat(4097));await assert.rejects(verify(d),/invalid_manifest/);
});
