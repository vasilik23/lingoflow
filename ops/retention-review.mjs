/** Offline, read-only retention review. Never sends warnings or deletes records. */
import { readFile, lstat, realpath, open } from 'node:fs/promises';
import { resolve, dirname, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DAY = 86400000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export class RetentionError extends Error {}
const fail = code => { throw new RetentionError(code); };
function instant(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value)) return null;
  const date = new Date(value);
  const [hour, minute, second] = value.slice(11, 19).split(':').map(Number);
  if (hour > 23 || minute > 59 || second > 59) return null;
  // Date.parse normalises impossible days: reject them explicitly.
  const [year, month, day] = value.slice(0, 10).split('-').map(Number);
  const maxDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return month >= 1 && month <= 12 && day >= 1 && day <= maxDay && Number.isFinite(date.valueOf()) ? date : null;
}
export { instant as retentionInstant };
function monthsLater(date, months) {
  const result = new Date(date);
  result.setUTCDate(1);
  result.setUTCMonth(result.getUTCMonth() + months);
  const last = new Date(Date.UTC(result.getUTCFullYear(), result.getUTCMonth() + 1, 0)).getUTCDate();
  result.setUTCDate(Math.min(date.getUTCDate(), last));
  return result;
}
const iso = date => date.toISOString();
function accountReview(row, now, captured) {
  const created = instant(row.created_at), activity = instant(row.last_activity_at);
  const base = { user_id: row.user_id, action: 'manual_review' };
  if (!created || !activity || created > activity || activity > captured) return { ...base, reason: 'activity_not_proven' };
  const warningAfter = monthsLater(activity, 12);
  if (now < warningAfter) return { ...base, action: 'active' };
  // Recent known use proves an account is active; missing coverage only blocks
  // an assertion of inactivity, never protects a deletion candidate.
  if (row.activity_complete !== true) return { ...base, reason: 'activity_not_proven' };
  if (!row.warning) return { ...base, action: 'warning_required', warning_not_before: iso(warningAfter) };
  const delivered = instant(row.warning.delivered_at), observedActivity = instant(row.warning.activity_at_delivery);
  if (!delivered || !observedActivity || delivered > captured || delivered < warningAfter || observedActivity.valueOf() !== activity.valueOf()) return { ...base, reason: 'warning_receipt_or_activity_invalid' };
  const deleteAfter = new Date(delivered.valueOf() + 30 * DAY);
  return { ...base, action: now >= deleteAfter ? 'deletion_review' : 'warning_wait', deletion_not_before: iso(deleteAfter), requires_live_activity_recheck: true };
}
function feedbackReview(row, now, captured) {
  const base = { id: row.id, action: 'keep' };
  if (!['new', 'reviewed', 'in_review', 'resolved', 'closed'].includes(row.status)) return { ...base, action: 'manual_review', reason: 'unknown_status' };
  if (!['resolved', 'closed'].includes(row.status)) return base;
  const created = instant(row.created_at), closed = instant(row.closed_at);
  if (!created || !closed || closed < created || closed > captured) return { ...base, action: 'manual_review', reason: 'closure_not_proven' };
  const expires = new Date(closed.valueOf() + 180 * DAY);
  return { ...base, action: now >= expires ? 'deletion_review' : 'keep', deletion_not_before: iso(expires), requires_live_status_recheck: true };
}
export function reviewRetention(snapshot, asOf) {
  const now = instant(asOf), captured = instant(snapshot?.captured_at);
  if (!now || !captured || captured > now || now - captured > DAY) fail('fresh_timestamped_snapshot_required');
  if (snapshot.version !== 1 || !Array.isArray(snapshot.accounts) || !Array.isArray(snapshot.feedback) || snapshot.accounts.length + snapshot.feedback.length > 10000) fail('invalid_snapshot');
  for (const [rows, field] of [[snapshot.accounts, 'user_id'], [snapshot.feedback, 'id']]) {
    const seen = new Set();
    for (const row of rows) {
      const id = row?.[field];
      if (typeof id !== 'string' || !UUID.test(id) || seen.has(id.toLowerCase())) fail('invalid_or_duplicate_record');
      seen.add(id.toLowerCase());
    }
  }
  const accounts = snapshot.accounts.map(row => accountReview(row, now, captured));
  const feedback = snapshot.feedback.map(row => feedbackReview(row, now, captured));
  const counts = rows => rows.reduce((acc, row) => ({ ...acc, [row.action]: (acc[row.action] || 0) + 1 }), {});
  return { version: 1, mode: 'review_only', reviewed_at: iso(now), captured_at: iso(captured), mutations: 0, notifications: 0, summary: { accounts: counts(accounts), feedback: counts(feedback) }, accounts, feedback };
}
function outsideRepository(path) {
  const rel = relative(ROOT, path);
  if (!rel || (!rel.startsWith('../') && rel !== '..' && !isAbsolute(rel))) fail('private_files_must_be_outside_repository');
}
export async function reviewFile(input, output, asOf) {
  const source = resolve(input), destination = resolve(output);
  const st = await lstat(source);
  if (!st.isFile() || st.isSymbolicLink() || st.nlink !== 1 || st.mode & 0o077 || st.size > 20 * 1024 * 1024) fail('private_regular_input_required');
  outsideRepository(await realpath(source));
  const parent = await realpath(dirname(destination)), parentStat = await lstat(parent);
  outsideRepository(parent);
  if (parentStat.mode & 0o077) fail('private_output_directory_required');
  const target = resolve(parent, destination.slice(destination.lastIndexOf('/') + 1));
  let snapshot;
  try { snapshot = JSON.parse(await readFile(source, 'utf8')); } catch { fail('invalid_snapshot'); }
  const report = reviewRetention(snapshot, asOf);
  const handle = await open(target, 'wx', 0o600);
  try { await handle.writeFile(JSON.stringify(report, null, 2) + '\n'); } finally { await handle.close(); }
  return { mode: report.mode, mutations: 0, notifications: 0, summary: report.summary };
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  if (args.length !== 2) {
    console.error(JSON.stringify({ error: 'usage_retention_review_private_input_private_output' }));
    process.exitCode = 2;
  } else reviewFile(args[0], args[1], new Date().toISOString()).then(result => console.log(JSON.stringify(result))).catch(error => {
    console.error(JSON.stringify({ error: error instanceof RetentionError ? error.message : 'retention_review_failed' }));
    process.exitCode = 2;
  });
}
