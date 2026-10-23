/** Operator-only preparation and verification. No SMTP, SQL writes or deletion. */
import { createHash } from 'node:crypto';
import { constants } from 'node:fs';
import { open, lstat, realpath } from 'node:fs/promises';
import { resolve, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { reviewRetention, RetentionError, retentionInstant } from './retention-review.mjs';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ZERO = '0'.repeat(64), DAY = 86400000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const fail = code => { throw new RetentionError(code); };
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const hash = value => createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');
const date = value => retentionInstant(value) || fail('valid_timestamp_required');
const ref = value => typeof value === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9._:/-]{2,199}$/.test(value);
const uuid = value => typeof value === 'string' && UUID.test(value);
const fields = (payload, names) => payload && Object.keys(payload).sort().join(',') === names.sort().join(',');
export const emptyJournal = () => ({ version: 1, head: ZERO, entries: [] });
function events(journal, now) {
  if (journal?.version !== 1 || !Array.isArray(journal.entries) || journal.entries.length > 10000) fail('invalid_journal');
  const notices = new Map(), seen = new Map();
  let previous = ZERO, previousTime = -Infinity;
  for (let i = 0; i < journal.entries.length; i++) {
    const entry = journal.entries[i];
    if (!fields(entry, ['event_id','type','at','payload','sequence','previous','hash'])) fail('invalid_journal_entry');
    const { hash: stored, ...body } = entry;
    const at = date(entry.at).valueOf(), p = entry.payload;
    if (!uuid(entry.event_id) || seen.has(entry.event_id) || entry.sequence !== i + 1 || entry.previous !== previous || hash(body) !== stored || at < previousTime || at > now) fail('journal_integrity_failed');
    if (entry.type === 'warning_submitted') {
      if (!fields(p, ['notice_id','user_id','activity_at']) || !uuid(p.notice_id) || !uuid(p.user_id) || date(p.activity_at) > at || notices.has(p.notice_id)) fail('invalid_warning_submission');
      notices.set(p.notice_id, { ...p, submitted_at: entry.at, delivered_at: null, failed: false });
    } else if (['warning_delivered','warning_failed'].includes(entry.type)) {
      if (!fields(p, ['notice_id','evidence_ref']) || !ref(p.evidence_ref)) fail('delivery_evidence_required');
      const notice = notices.get(p.notice_id);
      if (!notice || notice.failed || (entry.type === 'warning_delivered' && notice.delivered_at)) fail('invalid_delivery_transition');
      if (entry.type === 'warning_failed') notice.failed = true;
      else notice.delivered_at = entry.at;
    } else if (['account_deleted','feedback_deleted'].includes(entry.type)) {
      if (!fields(p, ['target_id','evidence_ref']) || !uuid(p.target_id) || !ref(p.evidence_ref)) fail('deletion_evidence_required');
    } else fail('unknown_journal_event');
    seen.set(entry.event_id, entry);
    previous = stored; previousTime = at;
  }
  if (journal.head !== previous) fail('journal_head_mismatch');
  return { notices, seen };
}
export function appendEvent(journal, event, asOf) {
  const now = date(asOf).valueOf(), state = events(journal, now);
  if (!fields(event, ['event_id','type','at','payload'])) fail('invalid_event');
  const existing = state.seen.get(event.event_id);
  if (existing) {
    const { sequence, previous, hash: ignored, ...old } = existing;
    if (JSON.stringify(canonical(old)) !== JSON.stringify(canonical(event))) fail('event_id_reused');
    return journal; // Retry of the same evidence is idempotent.
  }
  const body = { ...event, sequence: journal.entries.length + 1, previous: journal.head };
  const entry = { ...body, hash: hash(body) };
  const next = { version: 1, head: entry.hash, entries: [...journal.entries, entry] };
  events(next, now);
  return next;
}
function checkedSnapshot(snapshot, journal, asOf) {
  const now = date(asOf).valueOf(), { notices } = events(journal, now);
  // The snapshot is evidence of current use, never evidence of mail delivery.
  const accounts = (snapshot?.accounts || []).map(row => {
    const matching = [...notices.values()].filter(n => n.user_id === row.user_id && !n.failed && n.delivered_at && date(n.activity_at).valueOf() === date(row.last_activity_at).valueOf());
    const latest = matching.sort((a,b) => date(b.delivered_at) - date(a.delivered_at))[0];
    return { ...row, warning: latest ? { delivered_at: latest.delivered_at, activity_at_delivery: latest.activity_at } : null };
  });
  const input = { ...snapshot, accounts };
  reviewRetention(input, asOf);
  return input;
}
export function warningDraft(snapshot, request, asOf) {
  const input = { ...snapshot, accounts: (snapshot?.accounts || []).map(row => ({ ...row, warning: null })) };
  const review = reviewRetention(input, asOf);
  if (!uuid(request?.user_id) || !['ru','pl','en'].includes(request.language)) fail('warning_target_and_language_required');
  const candidate = review.accounts.find(row => row.user_id === request.user_id);
  if (candidate?.action !== 'warning_required') fail('warning_not_eligible');
  const activity = snapshot.accounts.find(row => row.user_id === request.user_id).last_activity_at;
  const earliest = new Date(date(asOf).valueOf() + 30 * DAY).toISOString().slice(0,10);
  const copy = {
    ru: ['LingoFlow: сохрани свой аккаунт', `Мы рассматриваем удаление аккаунта после 12 месяцев без использования. Удаление возможно не раньше ${earliest} (UTC) и не раньше чем через 30 дней после подтверждённой доставки этого предупреждения. Чтобы сохранить аккаунт, войди и открой приложение: https://lingoflow-learn.vercel.app/login/. Если считаешь это ошибкой или нужна помощь, напиши на lingoflow.privacy@gmail.com. Это служебное уведомление, не реклама.`],
    pl: ['LingoFlow: zachowaj swoje konto', `Rozważamy usunięcie konta po 12 miesiącach nieaktywności. Usunięcie może nastąpić nie wcześniej niż ${earliest} (UTC) i nie wcześniej niż 30 dni po potwierdzonym doręczeniu tego ostrzeżenia. Aby zachować konto, zaloguj się i otwórz aplikację: https://lingoflow-learn.vercel.app/login/. Jeśli to pomyłka lub potrzebujesz pomocy, napisz na lingoflow.privacy@gmail.com. To wiadomość dotycząca usługi, nie reklama.`],
    en: ['LingoFlow: keep your account', `We are considering deleting your account after 12 months without use. Deletion cannot occur before ${earliest} (UTC), or earlier than 30 days after confirmed delivery of this warning. To keep your account, sign in and open the app: https://lingoflow-learn.vercel.app/login/. If this is a mistake or you need help, contact lingoflow.privacy@gmail.com. This is a service notice, not advertising.`],
  }[request.language];
  return { mode: 'draft_only', user_id: request.user_id, activity_at: activity, language: request.language, subject: copy[0], body: copy[1], notifications: 0 };
}
function checkpoint(journal, evidence, asOf) {
  const now = date(asOf).valueOf();
  events(journal, now);
  if (evidence?.head !== journal.head || evidence.confirmed_external_copy !== true || !ref(evidence.storage_ref)) fail('independent_external_checkpoint_required');
  const verified = date(evidence.verified_at).valueOf();
  if (verified > now || now - verified > DAY || (journal.entries.length && verified < date(journal.entries.at(-1).at))) fail('fresh_external_checkpoint_required');
}
export function finalReview(snapshot, journal, evidence, asOf) {
  const input = checkedSnapshot(snapshot, journal, asOf);
  if (date(asOf) - date(snapshot.captured_at) > 5 * 60000) fail('live_recheck_within_five_minutes_required');
  checkpoint(journal, evidence, asOf);
  const deletedAccounts = new Set(journal.entries.filter(e => e.type === 'account_deleted').map(e => e.payload.target_id));
  const deletedFeedback = new Set(journal.entries.filter(e => e.type === 'feedback_deleted').map(e => e.payload.target_id));
  if (input.accounts.some(row => deletedAccounts.has(row.user_id)) || input.feedback.some(row => deletedFeedback.has(row.id))) fail('confirmed_deleted_data_present_requires_reconciliation');
  const review = reviewRetention(input, asOf);
  return { ...review, mode: 'operator_final_review_only', requires_transactional_recheck: true, remote_deletion_performed: false };
}
export function restorePlan(journal, evidence, asOf) {
  checkpoint(journal, evidence, asOf);
  const targets = type => [...new Set(journal.entries.filter(entry => entry.type === type).map(entry => entry.payload.target_id))].sort();
  return { mode: 'restore_plan_only', checkpoint_head: journal.head, account_ids: targets('account_deleted'), feedback_ids: targets('feedback_deleted'), enable_public_access: false, requires_post_checkpoint_reconciliation: true, mutations: 0 };
}
export function runLifecycle(request, asOf) {
  if (request?.action === 'warning') return warningDraft(request.snapshot, request.target, asOf);
  if (request?.action === 'record') return appendEvent(request.journal, request.event, asOf);
  if (request?.action === 'final-review') return finalReview(request.snapshot, request.journal, request.checkpoint, asOf);
  if (request?.action === 'restore') return restorePlan(request.journal, request.checkpoint, asOf);
  fail('unknown_lifecycle_action');
}
export async function runPrivateFile(input, output, asOf) {
  const path = resolve(input), st = await lstat(path);
  if (!st.isFile() || st.isSymbolicLink() || st.nlink !== 1 || st.mode & 0o077 || st.size > 20*1024*1024) fail('private_regular_input_required');
  const actual = await realpath(path), parent = await realpath(dirname(resolve(output)));
  for (const value of [actual,parent]) {
    const rel = relative(ROOT,value);
    if (!rel || (!rel.startsWith('../') && rel !== '..')) fail('private_files_must_be_outside_repository');
  }
  if ((await lstat(parent)).mode & 0o077) fail('private_output_directory_required');
  const handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  let request;
  try { request = JSON.parse(await handle.readFile('utf8')); } finally { await handle.close(); }
  const result = runLifecycle(request,asOf);
  const target = await open(resolve(parent,resolve(output).split('/').at(-1)), 'wx', 0o600);
  try { await target.writeFile(JSON.stringify(result,null,2)+'\n'); } finally { await target.close(); }
  return { action: request.action, output_written: true, mutations: 0, notifications: 0 };
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  (async()=>{
    if (process.argv.length!==4) fail('usage_retention_lifecycle_private_input_private_output');
    console.log(JSON.stringify(await runPrivateFile(process.argv[2],process.argv[3],new Date().toISOString())));
  })().catch(error=>{console.error(JSON.stringify({error:error instanceof RetentionError?error.message:'lifecycle_operation_failed'}));process.exitCode=2;});
}
