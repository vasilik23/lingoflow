#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync, spawn } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const state = path.join(root, '.local-audits');
fs.mkdirSync(state, { recursive: true, mode: 0o700 });
const lock = path.join(state, 'running');
try { fs.mkdirSync(lock); } catch (error) {
  if (error.code === 'EEXIST') { console.error('Audit already running; inspect .local-audits/running before removing a stale lock.'); process.exit(1); }
  throw error;
}
let child;
let timer;
let run;
let workspace;
let sha;
let started;
try {
  const now = new Date();
  started = now.toISOString();
  const stamp = now.toISOString().replace(/[:.]/g, '-');
  run = path.join(state, stamp);
  fs.mkdirSync(run, { mode: 0o700 });
  sha = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim();
  const changes = execFileSync('git', ['log', '--since=24 hours ago', '--format=%h %s', '--name-only', sha], { cwd: root, encoding: 'utf8', maxBuffer: 1024 * 1024 });
  const previous = fs.readdirSync(state).filter(name => /^\d{4}-\d{2}-\d{2}T/.test(name) && path.join(state, name) !== run)
    .sort().reverse().map(name => path.join(state, name, 'report.md')).find(file => fs.existsSync(file));
  const priorReport = previous ? fs.readFileSync(previous, 'utf8').slice(0, 30000) : 'No prior daily report.';
  workspace = path.join(run, 'workspace');
  fs.mkdirSync(workspace);
  const archive = path.join(run, 'source.tar');
  execFileSync('git', ['archive', '--format=tar', '--output', archive, sha], { cwd: root });
  execFileSync('/usr/bin/tar', ['-xf', archive, '-C', workspace]);
  fs.unlinkSync(archive);
  const prompt = fs.readFileSync(path.join(root, 'ops/daily-product-audit.md'), 'utf8');
  const report = path.join(run, 'report.md');
  const log = fs.openSync(path.join(run, 'runner.log'), 'w', 0o600);
  child = spawn(process.env.LINGOFLOW_AUDIT_CODEX || 'codex', [
    'exec', '--approve-for-me', '--ephemeral', '--skip-git-repo-check',
    '--cd', workspace, '--color', 'never', '--output-last-message', report, '-'
  ], { cwd: workspace, detached: true, stdio: ['pipe', log, log] });
  fs.closeSync(log);
  child.stdin.on('error', () => {});
  child.stdin.end(`Snapshot: ${sha}\nStarted: ${started}\nRecent commits and paths (24h):\n${changes}\nPrevious daily report (may be truncated):\n${priorReport}\nCurrent task:\n${prompt}`);
  timer = setTimeout(() => {
    try { process.kill(-child.pid, 'SIGTERM'); } catch {}
    setTimeout(() => { try { process.kill(-child.pid, 'SIGKILL'); } catch {} }, 5000).unref();
  }, 15 * 60 * 1000);
  const code = await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('close', resolve);
  });
  const completed = code === 0 && fs.existsSync(report) && fs.statSync(report).size > 0;
  const evidence = path.join(workspace, 'audit-evidence');
  if (fs.existsSync(evidence) && fs.lstatSync(evidence).isDirectory()) fs.renameSync(evidence, path.join(run, 'evidence'));
  fs.writeFileSync(path.join(run, 'status.json'), JSON.stringify({ sha, started: now.toISOString(), finished: new Date().toISOString(), status: completed ? 'report_created' : 'failed', exitCode: code }, null, 2));
  if (!completed) throw new Error('Audit failed or did not produce a report; inspect runner.log.');
  console.log(`Audit report: ${report}`);
} catch (error) {
  if (run) {
    fs.writeFileSync(path.join(run, 'failure.txt'), `${error.message}\n`);
    const status = path.join(run, 'status.json');
    if (!fs.existsSync(status)) fs.writeFileSync(status, JSON.stringify({ sha, started, finished: new Date().toISOString(), status: 'failed', error: error.message }, null, 2));
  }
  console.error(error.message);
  process.exitCode = 1;
} finally {
  clearTimeout(timer);
  if (workspace) fs.rmSync(workspace, { recursive: true, force: true });
  fs.rmdirSync(lock);
}
