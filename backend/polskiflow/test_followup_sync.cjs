const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/learning/static/polskiflow/lesson-result-sync.js', 'utf8');

function mount(createQueue, language = null) {
  const handlers = {}, events = {};
  const saved = { hidden: true, removeAttribute() { this.hidden = false; } };
  const pending = { hidden: false, setAttribute() { this.hidden = true; }, removeAttribute() { this.hidden = false; } };
  const status = {};
  const retry = { hidden: true, addEventListener(name, callback) { events[name] = callback; } };
  const panel = {
    dataset: { queueNamespace: 'fixture', csrfToken: 'fixture', resultPayload: JSON.stringify({ event_id: 'current-event' }) },
    querySelector(selector) { return selector === '[data-sync-status]' ? status : retry; },
    closest() { return { querySelector(selector) { return selector === '[data-followup-saved]' ? saved : pending; } }; },
  };
  const window = { addEventListener(name, callback) { events[name] = callback; }, PolskiFlowResultQueue: { createQueue } };
  if (language) {
    vm.runInNewContext(fs.readFileSync(__dirname + `/learning/static/polskiflow/i18n-${language}.js`, 'utf8'), { window });
    const messages = language === 'pl' ? window.PolskiFlowPolishMessages : window.PolskiFlowEnglishMessages;
    window.PolskiFlowI18n = { t: (text) => messages[text] || text };
  }
  const document = { querySelectorAll() { return []; }, addEventListener(name, callback) { handlers[name] = callback; } };
  vm.runInNewContext(source, { window, document });
  const swap = () => handlers['htmx:afterSwap']({ target: { querySelectorAll() { return [panel]; } } });
  swap();
  return { saved, pending, status, retry, events, swap };
}
const tick = () => new Promise((resolve) => setImmediate(resolve));

(async () => {
  let notify, resolveFlush, flushes = 0;
  const page = mount(({ onStatus }) => {
    notify = onStatus;
    return { async enqueue() { onStatus({ state: 'queued', eventId: 'current-event' }); },
      flushSession() { flushes++; return new Promise((resolve) => { resolveFlush = resolve; }); } };
  });
  await tick();
  notify({ state: 'sent', eventId: 'older-event' });
  assert.notEqual(page.status.textContent, 'Результат сохранён.');
  assert.equal(page.retry.hidden, false);
  assert.equal(page.saved.hidden, true, 'Another queued result cannot schedule this lesson');
  assert.equal(page.pending.hidden, false);
  notify({ state: 'auth-required', eventId: 'older-event' });
  assert.equal(page.status.textContent, 'Войди снова, затем повтори отправку.', 'An older event can block authentication for the entire queue');
  notify({ state: 'synced', pending: 0 });
  assert.equal(page.saved.hidden, true, 'Global queue status is not this result acknowledgement');
  page.events.online(); page.events.click(); page.swap();
  assert.equal(flushes, 1, 'Concurrent online/click/HTMX events must not start duplicate flushes');
  notify({ state: 'sent', eventId: 'current-event' });
  assert.equal(page.saved.hidden, true, 'An event receipt cannot promise a repeat cancelled by a newer success');
  assert.equal(page.pending.hidden, false);
  assert.equal(page.pending.textContent, 'Результат сохранён. Открой план, чтобы увидеть актуальные повторения.');
  assert.equal(page.retry.hidden, true);
  assert.equal(page.status.textContent, 'Результат сохранён.');
  notify({ state: 'needs-attention', eventId: 'other-event' });
  notify({ state: 'pending', pending: 1 });
  assert.equal(page.status.textContent, 'Результат сохранён.', 'Another pending result cannot undo this acknowledgement');
  resolveFlush(); await tick();
  page.events.online();
  assert.equal(flushes, 2, 'Later online events must still flush other pending lessons');
  assert.equal(page.status.textContent, 'Результат сохранён.', 'Background work must not replace this confirmed result');
  resolveFlush(); await tick();
  const attention = mount(({ onStatus }) => ({ async enqueue() {}, async flushSession() {
    onStatus({ state: 'needs-attention', eventId: 'current-event' });
    onStatus({ state: 'pending', pending: 1 });
  } }));
  await tick();
  assert.equal(attention.status.textContent, 'Результат требует проверки. Попробуй ещё раз позже.');
  assert.equal(attention.retry.hidden, true, 'Do not offer a retry that skips a permanently rejected event');
  const unavailable = mount(() => { throw new Error('IndexedDB unavailable'); });
  await tick();
  assert.equal(unavailable.status.textContent, 'Локальное сохранение недоступно. Вернись к уроку позже.');
  assert.equal(unavailable.saved.hidden, true);
  for (const language of ['pl', 'en']) {
    const localized = mount(({ onStatus }) => ({ async enqueue() {}, async flushSession() {
      onStatus({ state: 'sent', eventId: 'current-event' });
    } }), language);
    await tick();
    assert.equal(localized.pending.textContent, language === 'pl'
      ? 'Wynik został zapisany. Otwórz plan, aby zobaczyć aktualne powtórki.'
      : 'Your result was saved. Open your plan to see the current reviews.');
  }
})().catch((error) => { console.error(error); process.exit(1); });
