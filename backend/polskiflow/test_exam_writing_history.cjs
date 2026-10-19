const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-exam-writing.js'), 'utf8');
const key = 'lingoflow-exam-writing-v1:fixture', store = new Map();
let now = 1700000000000, serial = 0;
class El extends EventTarget { constructor() { super(); this.value = ''; this.textContent = ''; this.hidden = false; this.dataset = {}; } focus() {} }
function page(owner = 'fixture') {
  const editors = [new El(), new El()], pending = [], requests = [];
  editors.forEach(e => { e.closest = () => ({dataset: {target: '50'}, querySelector: () => new El()}); });
  const names = ['status','clock','start','finish','dialog','storage','result','cancel','confirm','again','history-status','history-retry'];
  const nodes = Object.fromEntries(names.map(n => [n, new El()]));
  nodes.dialog.close = () => {}; nodes.dialog.showModal = () => {};
  const root = {dataset: {set: '1', owner}, querySelector: s => nodes[s.slice(11, -1)], querySelectorAll: s => s === '[data-exam-draft]' ? editors : []};
  const win = new EventTarget(); win.crypto = {randomUUID: () => `00000000-0000-4000-8000-${String(++serial).padStart(12, '0')}`};
  const timers = new Map(); let timerId = 0;
  win.setTimeout = fn => { timers.set(++timerId, fn); return timerId; };
  win.clearTimeout = id => timers.delete(id);
  class Clock extends Date { static now() { return now; } }
  const tickers = [];
  vm.runInNewContext(source, {
    document: {querySelector: s => s.includes('csrfmiddlewaretoken') ? {value: 'csrf'} : root, querySelectorAll: () => [], addEventListener() {}},
    window: win, localStorage: {getItem: k => store.get(k) || null, setItem: (k,v) => store.set(k,v), removeItem: k => store.delete(k), key: i => [...store.keys()][i], get length() { return store.size; }},
    fetch: (url, options) => { requests.push({url, options}); return new Promise((resolve, reject) => { pending.push({resolve, reject}); options.signal.addEventListener('abort', () => reject(Error('aborted'))); }); },
    location: {replace() {}}, Date: Clock, Event, AbortController, setInterval: fn => tickers.push(fn),
  });
  return {nodes, editors, requests, pending, win, tick: () => tickers[0](), timeout: () => [...timers.values()].at(-1)()};
}
const click = el => el.dispatchEvent(new Event('click'));
const settle = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  let p = page(); click(p.nodes.start); p.editors[0].value = 'Private essay one'; p.editors[1].value = 'Private essay two';
  now += 120000; click(p.nodes.confirm);
  const request = p.requests[0], payload = JSON.parse(request.options.body);
  assert.deepEqual(Object.keys(payload).sort(), ['attempt_id','set_id','content_version','started_at','finished_at','timed_out','remaining_seconds','words_a','words_b'].sort());
  assert.equal(payload.remaining_seconds, 4380); assert.equal(payload.words_a, 3);
  assert.equal(request.options.credentials, 'same-origin'); assert.equal(request.options.headers['X-CSRFToken'], 'csrf');
  assert.equal(request.options.headers['X-LingoFlow-Writing-Owner'], 'fixture');
  assert(!request.options.body.includes('Private'));
  p.pending[0].reject(Error('network')); await settle(); assert.equal(p.editors[0].value, 'Private essay one');
  click(p.nodes['history-retry']);
  assert.equal(p.nodes['history-retry'].disabled, true);
  p.timeout(); await settle();
  assert.equal(p.requests.at(-1).options.signal.aborted, true);
  assert.equal(p.nodes['history-retry'].disabled, false, 'hung request must allow manual retry after timeout');
  assert.equal(p.requests.at(-1).options.body, request.options.body);
  for (const status of [503, 409, 400]) {
    click(p.nodes['history-retry']);
    assert.equal(p.requests.at(-1).options.body, request.options.body);
    p.pending.at(-1).resolve({ok: false, status, json: async () => ({saved: false})}); await settle();
    assert.equal(p.nodes['history-retry'].hidden, false);
    assert.equal(p.editors[0].value, 'Private essay one');
    assert.match(p.nodes['history-status'].textContent, /пока не сохранена/);
  }
  click(p.nodes['history-retry']);
  p.pending.at(-1).resolve({ok: true, json: async () => ({saved: true, attempt_id: payload.attempt_id})}); await settle();
  assert.match(p.nodes['history-status'].textContent, /сохранена в аккаунте/);
  // Lost acknowledgement retries the exact immutable payload on refresh.
  let saved = JSON.parse(store.get(key)); saved['1'].historySaved = false; store.set(key, JSON.stringify(saved));
  saved['1'].historyPayload.text = 'Never transmit this essay'; store.set(key, JSON.stringify(saved));
  p = page(); assert.equal(p.requests[0].options.body, request.options.body);
  click(p.nodes.again); click(p.nodes.start);
  const replacement = JSON.parse(store.get(key))['1'].attemptId;
  p.pending[0].resolve({ok: true, json: async () => ({saved: true, attempt_id: payload.attempt_id})}); await settle();
  assert.equal(JSON.parse(store.get(key))['1'].attemptId, replacement); assert(!JSON.parse(store.get(key))['1'].historySaved);
  now += 6000000; p.tick();
  const timeout = JSON.parse(p.requests[1].options.body);
  assert.equal(timeout.timed_out, true); assert.equal(timeout.remaining_seconds, 0);
  assert.equal(Date.parse(timeout.finished_at) - Date.parse(timeout.started_at), 4500000);
  // A queued replacement remains pending even when a legacy editor has no summary.
  for (const k of [...store.keys()]) if (k.startsWith('lingoflow-exam-writing-history-v1:')) store.delete(k);
  store.set(key, JSON.stringify({'1': {status: 'finished', texts: ['legacy', ''], deadline: now, remaining: 0}}));
  p = page(); assert.equal(p.requests.length, 0); assert.match(p.nodes['history-status'].textContent, /только в браузере/);
  store.clear();
  p = page(); click(p.nodes.start); p.editors[0].value = 'Private A'; click(p.nodes.confirm);
  const a = JSON.parse(p.requests[0].options.body);
  p.pending[0].reject(Error('offline')); await settle();
  click(p.nodes.again); click(p.nodes.start); p.editors[0].value = 'Private B';
  p.editors[0].dispatchEvent(new Event('input'));
  p = page(); // Refresh while B is still running must retain A in its own queue.
  assert.equal(p.editors[0].value, 'Private B');
  assert.equal(JSON.parse(p.requests[0].options.body).attempt_id, a.attempt_id);
  click(p.nodes.confirm);
  const b = p.requests.map(r => JSON.parse(r.options.body)).find(r => r.attempt_id !== a.attempt_id);
  for (const pending of p.pending) pending.reject(Error('offline')); await settle();
  assert.notEqual(a.attempt_id, b.attempt_id);
  const other = page('another-owner'); assert.equal(other.requests.length, 0, 'owner isolation');
  p = page(); assert.equal(p.requests.length, 2, 'both immutable summaries survive replacement and refresh');
  const savedIds = new Set();
  p.requests.forEach((r, i) => {
    const payload = JSON.parse(r.options.body);
    assert(!r.options.body.includes('Private'));
    savedIds.add(payload.attempt_id);
    p.pending[i].resolve({ok: true, json: async () => ({saved: true, attempt_id: payload.attempt_id})});
  });
  await settle(); assert.equal(savedIds.size, 2);
  p = page(); assert.equal(p.requests.length, 0, 'ACKed summaries are not sent again');
  // Recovering connectivity retries metadata without a refresh.
  click(p.nodes.again); click(p.nodes.start); click(p.nodes.confirm);
  p.pending[0].reject(Error('offline')); await settle();
  p.win.dispatchEvent(new Event('online')); assert.equal(p.requests.length, 2);
  assert.equal(p.requests[0].options.body, p.requests[1].options.body);
  console.log('Exam writing account history: aggregate privacy, retry, reload, stale acknowledgement, timeout and legacy PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
