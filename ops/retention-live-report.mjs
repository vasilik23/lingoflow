/** Consume a Management API SQL result on stdin, save private snapshot + review. */
import { open, lstat, realpath } from 'node:fs/promises';
import { resolve, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { reviewRetention, reviewFile, RetentionError } from './retention-review.mjs';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export function snapshotFromResult(result) {
  const snapshot = Array.isArray(result) && result.length === 1 ? result[0]?.retention_snapshot : null;
  if (!snapshot || typeof snapshot !== 'object') throw new RetentionError('single_retention_snapshot_result_required');
  // Validate before touching disk and never propagate arbitrary query-result fields.
  reviewRetention(snapshot, new Date().toISOString());
  return {
    version: snapshot.version, captured_at: snapshot.captured_at,
    accounts: snapshot.accounts.map(row => ({
      user_id: row.user_id, created_at: row.created_at, last_activity_at: row.last_activity_at,
      activity_complete: row.activity_complete === true, tracking_started_at: row.tracking_started_at ?? null,
      warning: row.warning ? { delivered_at: row.warning.delivered_at, activity_at_delivery: row.warning.activity_at_delivery } : null,
    })),
    feedback: snapshot.feedback.map(row => ({ id: row.id, status: row.status, created_at: row.created_at, closed_at: row.closed_at ?? null })),
  };
}
export async function writeLiveReport(result, directory) {
  const path = resolve(directory), st = await lstat(path);
  if (!st.isDirectory() || st.isSymbolicLink() || st.mode & 0o077) throw new RetentionError('private_directory_required');
  const actual = await realpath(path), rel = relative(ROOT, actual);
  if (!rel || (!rel.startsWith('../') && rel !== '..')) throw new RetentionError('private_files_must_be_outside_repository');
  const snapshot = snapshotFromResult(result);
  const handle = await open(resolve(actual, 'snapshot.json'), 'wx', 0o600);
  try { await handle.writeFile(JSON.stringify(snapshot) + '\n'); } finally { await handle.close(); }
  return reviewFile(resolve(actual, 'snapshot.json'), resolve(actual, 'report.json'), new Date().toISOString());
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  (async () => {
    if (process.argv.length !== 3) throw new RetentionError('usage_retention_live_report_private_directory');
    let text = '', bytes = 0;
    for await (const chunk of process.stdin) {
      bytes += chunk.length;
      if (bytes > 20 * 1024 * 1024) throw new RetentionError('result_too_large');
      text += chunk.toString('utf8');
    }
    let result;
    try { result = JSON.parse(text); } catch { throw new RetentionError('invalid_query_result'); }
    console.log(JSON.stringify(await writeLiveReport(result, process.argv[2])));
  })().catch(error => {
    console.error(JSON.stringify({ error: error instanceof RetentionError ? error.message : 'retention_live_report_failed' }));
    process.exitCode = 2;
  });
}
