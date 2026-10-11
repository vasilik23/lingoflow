import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync, spawn } from 'node:child_process';

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'lingoflow-audit-check-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'ops'));
  fs.copyFileSync(new URL('./daily-product-audit.mjs', import.meta.url), path.join(root, 'ops/daily-product-audit.mjs'));
  fs.writeFileSync(path.join(root, 'ops/daily-product-audit.md'), 'Synthetic audit task.');
  fs.writeFileSync(path.join(root, '.gitignore'), '.env\n.local-audits/\n');
  execFileSync('git', ['init', '-q'], { cwd: root });
  execFileSync('git', ['add', '.'], { cwd: root });
  execFileSync('git', ['-c', 'user.name=Audit fixture', '-c', 'user.email=audit@example.invalid', 'commit', '-qm', 'Synthetic snapshot'], { cwd: root });
  fs.writeFileSync(path.join(root, '.env'), 'SYNTHETIC_ONLY=true');
  fs.writeFileSync(path.join(root, 'uncommitted.txt'), 'Must not enter the audit snapshot.');
  const cli = path.join(root, 'fake-codex.mjs');
  fs.writeFileSync(cli, `#!${process.execPath}
import fs from 'node:fs';
if (fs.existsSync('.env') || fs.existsSync('uncommitted.txt')) process.exit(9);
let prompt = ''; for await (const chunk of process.stdin) prompt += chunk;
if (!prompt.includes('Snapshot:') || !prompt.includes('Synthetic audit task.')) process.exit(8);
if (process.env.FAKE_DELAY) await new Promise(resolve => setTimeout(resolve, 1000));
if (process.env.FAKE_NO_REPORT) process.exit(0);
const report = process.argv[process.argv.indexOf('--output-last-message') + 1];
fs.mkdirSync('audit-evidence'); fs.writeFileSync('audit-evidence/observation.json', '{}');
fs.writeFileSync(report, '# Synthetic report');
`);
  fs.chmodSync(cli, 0o700);
  return { root, cli };
}
function start({ root, cli }, extra = {}) {
  const child = spawn(process.execPath, [path.join(root, 'ops/daily-product-audit.mjs')], {
    cwd: root, env: { ...process.env, LINGOFLOW_AUDIT_CODEX: cli, ...extra }, stdio: ['ignore', 'pipe', 'pipe']
  });
  let output = '';
  child.stdout.on('data', data => { output += data; });
  child.stderr.on('data', data => { output += data; });
  const done = new Promise((resolve, reject) => { child.once('error', reject); child.once('close', code => resolve({ code, output })); });
  return { child, done };
}
function result(root) {
  const state = path.join(root, '.local-audits');
  const run = path.join(state, fs.readdirSync(state).find(name => /^\d{4}-/.test(name)));
  return { run, status: JSON.parse(fs.readFileSync(path.join(run, 'status.json'))) };
}

test('snapshot excludes private/uncommitted files and preserves report/evidence', async t => {
  const env = fixture(t);
  assert.equal((await start(env).done).code, 0);
  const { run, status } = result(env.root);
  assert.equal(status.status, 'report_created');
  assert.equal(status.sha, execFileSync('git', ['rev-parse', 'HEAD'], { cwd: env.root, encoding: 'utf8' }).trim());
  assert.equal(fs.readFileSync(path.join(run, 'report.md'), 'utf8'), '# Synthetic report');
  assert.ok(fs.existsSync(path.join(run, 'evidence/observation.json')));
  assert.ok(!fs.existsSync(path.join(run, 'workspace')));
  assert.ok(!fs.existsSync(path.join(env.root, '.local-audits/running')));
});

test('CLI exit zero without a report is a failure and releases the lock', async t => {
  const env = fixture(t);
  assert.equal((await start(env, { FAKE_NO_REPORT: '1' }).done).code, 1);
  const { run, status } = result(env.root);
  assert.equal(status.status, 'failed');
  assert.ok(fs.existsSync(path.join(run, 'failure.txt')));
  assert.ok(!fs.existsSync(path.join(run, 'workspace')));
  assert.ok(!fs.existsSync(path.join(env.root, '.local-audits/running')));
});

test('concurrent invocation is rejected without interrupting the first audit', async t => {
  const env = fixture(t);
  const first = start(env, { FAKE_DELAY: '1' });
  const lock = path.join(env.root, '.local-audits/running');
  for (let i = 0; i < 100 && !fs.existsSync(lock); i++) await new Promise(resolve => setTimeout(resolve, 10));
  assert.ok(fs.existsSync(lock));
  const second = await start(env).done;
  assert.equal(second.code, 1);
  assert.match(second.output, /Audit already running/);
  assert.equal((await first.done).code, 0);
  assert.equal(result(env.root).status.status, 'report_created');
});
