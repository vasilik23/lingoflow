import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, chmod, stat, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { reviewRetention, reviewFile } from './retention-review.mjs';
const now = '2026-10-23T08:00:00Z';
const id = '11111111-1111-4111-8111-111111111111';
const row = { user_id: id, created_at: '2024-01-01T00:00:00Z', last_activity_at: '2025-09-01T00:00:00Z', activity_complete: true };
const snapshot = (accounts = [row], feedback = []) => ({ version: 1, captured_at: now, accounts, feedback });
const account = (extra, at = now) => reviewRetention({ ...snapshot([{ ...row, ...extra }]), captured_at: at }, at).accounts[0];
const warning = { delivered_at: '2026-09-22T08:00:00Z', activity_at_delivery: row.last_activity_at };
test('no delivery receipt means warning review, never deletion', () => {
  assert.equal(account({}).action, 'warning_required');
  const out = reviewRetention(snapshot(), now);
  assert.equal(out.mode, 'review_only'); assert.equal(out.mutations, 0); assert.equal(out.notifications, 0);
});
test('complete activity required; profile lesson date alone is insufficient', () => {
  for (const activity_complete of [undefined, false, 'true']) assert.equal(account({ activity_complete }).reason, 'activity_not_proven');
  assert.equal(account({ last_activity_at: null }).reason, 'activity_not_proven');
});
test('recent use and account creation prevent deletion', () => {
  assert.equal(account({ last_activity_at: '2026-10-22T08:00:00Z', warning }).action, 'active');
  assert.equal(account({ created_at: now, last_activity_at: now }).action, 'active');
});
test('12 calendar months, including leap-day clamping', () => {
  const extra = { created_at: '2023-01-01T00:00:00Z', last_activity_at: '2024-02-29T08:00:00Z' };
  assert.equal(account(extra, '2025-02-28T07:59:59Z').action, 'active');
  assert.equal(account(extra, '2025-02-28T08:00:00Z').action, 'warning_required');
});
test('exact 30-day boundary after proven delivery and live recheck required', () => {
  assert.equal(account({ warning }, '2026-10-22T07:59:59Z').action, 'warning_wait');
  const result = account({ warning }, '2026-10-22T08:00:00Z');
  assert.equal(result.action, 'deletion_review'); assert.equal(result.requires_live_activity_recheck, true);
});
test('activity since warning invalidates receipt even if account remains old', () => {
  assert.equal(account({ last_activity_at: '2025-09-02T00:00:00Z', warning }).action, 'manual_review');
});
test('early, future, malformed or undelivered warnings fail closed', () => {
  for (const delivered_at of ['2026-08-31T23:59:59Z', '2027-01-01T00:00:00Z', null, '2026-02-30T00:00:00Z']) {
    assert.equal(account({ warning: { ...warning, delivered_at } }).action, 'manual_review');
  }
});
test('future, impossible or pre-creation activity fails closed', () => {
  for (const last_activity_at of ['2027-01-01T00:00:00Z', '2025-02-30T00:00:00Z', '2023-01-01T00:00:00Z']) assert.equal(account({ last_activity_at }).action, 'manual_review');
});
test('stale snapshot never authorises a review action', () => {
  assert.throws(() => reviewRetention({ ...snapshot(), captured_at: '2026-10-21T07:00:00Z' }, now));
  assert.throws(() => reviewRetention({ ...snapshot(), captured_at: '2027-01-01T00:00:00Z' }, now));
});
test('duplicate identifiers, non-UUID identifiers and malformed envelopes rejected', () => {
  assert.throws(() => reviewRetention(snapshot([row, row]), now));
  assert.throws(() => reviewRetention(snapshot([{ ...row, user_id: 'email@example.com' }]), now));
  assert.throws(() => reviewRetention({ ...snapshot(), accounts: null }, now));
});
test('feedback expiry starts at closure, not creation; exact 180-day boundary', () => {
  const feedback = { id, status: 'resolved', created_at: '2024-01-01T00:00:00Z', closed_at: '2026-04-26T08:00:00Z' };
  const out = reviewRetention(snapshot([], [feedback]), now).feedback[0];
  assert.equal(out.action, 'deletion_review'); assert.equal(out.requires_live_status_recheck, true);
  assert.equal(reviewRetention(snapshot([], [{ ...feedback, closed_at: '2026-04-26T08:00:01Z' }]), now).feedback[0].action, 'keep');
});
test('unclosed feedback kept, closed feedback with no valid closure held for review', () => {
  for (const status of ['new', 'reviewed', 'in_review']) assert.equal(reviewRetention(snapshot([], [{ id, status }]), now).feedback[0].action, 'keep');
  for (const closed_at of [null, now, '2023-01-01T00:00:00Z']) {
    const out = reviewRetention(snapshot([], [{ id, status: 'closed', created_at: now, closed_at }]), now).feedback[0];
    assert.equal(out.action, closed_at === now ? 'keep' : 'manual_review');
  }
});
test('report does not echo email, message, passwords or arbitrary input fields', () => {
  const out = reviewRetention(snapshot([{ ...row, email: 'private@example.com', password: 'secret' }], [{ id, status: 'new', message: 'private text' }]), now);
  for (const secret of ['private@example.com', 'secret', 'private text']) assert(!JSON.stringify(out).includes(secret));
});
test('private report is exclusive, mode 0600; symlinks and public input rejected', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'lf-retention-test-'));
  try {
    await chmod(dir, 0o700);
    const input = join(dir, 'input.json'), output = join(dir, 'report.json');
    await writeFile(input, JSON.stringify(snapshot()), { mode: 0o600 });
    const summary = await reviewFile(input, output, now);
    assert.equal((await stat(output)).mode & 0o777, 0o600);
    assert(!JSON.stringify(summary).includes(id));
    await assert.rejects(reviewFile(input, output, now));
    await symlink(input, join(dir, 'link.json'));
    await assert.rejects(reviewFile(join(dir, 'link.json'), join(dir, 'other.json'), now));
    await chmod(input, 0o644);
    await assert.rejects(reviewFile(input, join(dir, 'other.json'), now));
  } finally { await rm(dir, { recursive: true, force: true }); }
});
