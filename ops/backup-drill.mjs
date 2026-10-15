/** Operator-only tooling. SQL archives must come from a trusted Supabase CLI dump. */
import { createHash } from 'node:crypto';
import { createReadStream, constants } from 'node:fs';
import { open, lstat, realpath, writeFile } from 'node:fs/promises';
import { dirname, resolve, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

export const PROJECT = 'habcghygjaynknkcbirz';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const FILES = ['roles.sql', 'schema.sql', 'data.sql'];
const MANIFEST = 'manifest.json';
const EMPTY_TARGET = "SELECT (SELECT count(*) FROM pg_tables WHERE schemaname IN ('public','private')) = 0 AND (SELECT count(*) FROM auth.users) = 0;";
export class DrillError extends Error {}
const fail = code => { throw new DrillError(code); };

async function privateDirectory(directory) {
  const path = resolve(directory);
  const stat = await lstat(path);
  if (!stat.isDirectory() || stat.isSymbolicLink() || (stat.mode & 0o077)) fail('private_directory_required');
  const actual = await realpath(path);
  const rel = relative(ROOT, actual);
  if (!rel || (!rel.startsWith('..' + '/') && rel !== '..' && !isAbsolute(rel))) fail('archive_must_be_outside_repository');
  return actual;
}
async function inspectFile(directory, name, maxBytes = Infinity) {
  const path = resolve(directory, name);
  const stat = await lstat(path);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.nlink !== 1 || (stat.mode & 0o077) || stat.size === 0) fail('private_regular_file_required');
  if (stat.size > maxBytes) fail('invalid_manifest');
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(path, { flags: constants.O_RDONLY | constants.O_NOFOLLOW })) hash.update(chunk);
  return { bytes: stat.size, sha256: hash.digest('hex') };
}
export async function seal(directory) {
  const path = await privateDirectory(directory);
  const files = {};
  for (const name of FILES) files[name] = await inspectFile(path, name);
  const manifest = { version: 1, project: PROJECT, sealed_at: new Date().toISOString(), files };
  await writeFile(resolve(path, MANIFEST), JSON.stringify(manifest, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
  return { status: 'sealed', files: FILES.length, restored: false };
}
export async function verify(directory) {
  const path = await privateDirectory(directory);
  await inspectFile(path, MANIFEST, 4096);
  const handle = await open(resolve(path, MANIFEST), constants.O_RDONLY | constants.O_NOFOLLOW);
  let manifest;
  try {
    if ((await handle.stat()).size > 4096) fail('invalid_manifest');
    manifest = JSON.parse(await handle.readFile('utf8'));
  } catch { fail('invalid_manifest'); } finally { await handle.close(); }
  if (manifest?.version !== 1 || manifest.project !== PROJECT || typeof manifest.sealed_at !== 'string'
      || !Number.isFinite(Date.parse(manifest.sealed_at)) || !manifest.files
      || Object.keys(manifest).sort().join() !== ['files','project','sealed_at','version'].join()
      || Object.keys(manifest.files).sort().join() !== [...FILES].sort().join()) fail('invalid_manifest');
  for (const name of FILES) {
    const actual = await inspectFile(path, name), expected = manifest.files[name];
    if (!expected || Object.keys(expected).sort().join() !== 'bytes,sha256'
        || actual.bytes !== expected.bytes || actual.sha256 !== expected.sha256) fail('archive_integrity_failed');
  }
  return { status: 'verified', files: FILES.length, restored: false };
}
export function restoreConfig(port, password) {
  if (!/^[0-9]{4,5}$/.test(String(port)) || Number(port) < 1024 || Number(port) > 65535) fail('explicit_local_port_required');
  if (typeof password !== 'string' || !password || password.includes('\0')) fail('local_restore_password_required');
  return {
    args: ['-X', '--no-password', '--host=127.0.0.1', `--port=${port}`, '--username=postgres', '--dbname=postgres'],
    // No inherited PGHOSTADDR, PGSERVICE, PGOPTIONS, .psqlrc or .pgpass overrides.
    env: { PATH: process.env.PATH, PGPASSWORD: password, PGPASSFILE: '/dev/null', PGCONNECT_TIMEOUT: '5' },
  };
}
function psql(config, args, run, output = false) {
  const result = run('psql', [...config.args, ...args], {
    env: config.env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'],
    timeout: 300_000, maxBuffer: 1024 * 1024,
  });
  if (result.error || result.status !== 0) fail('local_psql_failed');
  return output ? result.stdout.trim() : null;
}
export async function restoreLocal(directory, port, password, execute, run = spawnSync) {
  if (execute !== true) fail('explicit_execute_required');
  const config = restoreConfig(port, password);
  await verify(directory);
  if (psql(config, ['--tuples-only', '--no-align', '--command', EMPTY_TARGET], run, true) !== 't') fail('empty_local_supabase_required');
  const path = await privateDirectory(directory);
  // Each archive is fixed by name. No user-supplied SQL, host, database or flags.
  psql(config, ['--single-transaction', '--variable=ON_ERROR_STOP=1',
    '--file', resolve(path, 'roles.sql'), '--file', resolve(path, 'schema.sql'),
    '--command', 'SET session_replication_role = replica', '--file', resolve(path, 'data.sql')], run);
  return { status: 'local_import_completed', files: FILES.length, restored: true, acceptance_required: true };
}

async function main(args) {
  const [action, directory, ...extra] = args;
  if (!directory || !['seal','verify','restore-local'].includes(action)) fail('usage_seal_verify_or_restore_local');
  if (action !== 'restore-local') {
    if (extra.length) fail('unexpected_arguments');
    return action === 'seal' ? seal(directory) : verify(directory);
  }
  if (extra.length !== 3 || extra[0] !== '--port' || extra[2] !== '--execute') fail('usage_restore_local_port_execute');
  return restoreLocal(directory, extra[1], process.env.LINGOFLOW_RESTORE_PASSWORD, true);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(result => console.log(JSON.stringify(result))).catch(error => {
    // Never print raw filesystem, subprocess or SQL errors: they can contain data/secrets.
    console.error(JSON.stringify({ status: 'failed', code: error instanceof DrillError ? error.message : 'archive_operation_failed' }));
    process.exitCode = 2;
  });
}
