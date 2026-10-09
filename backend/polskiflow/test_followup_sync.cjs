const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const handlers = {};
const saved = { hidden: true, removeAttribute() { this.hidden = false; } };
const pending = { hidden: false, setAttribute() { this.hidden = true; } };
const card = { querySelector(selector) { return selector === '[data-followup-saved]' ? saved : pending; } };
const status = {};
const retry = { addEventListener() {} };
const panel = {
  dataset: { queueNamespace: 'fixture', csrfToken: 'fixture', resultPayload: JSON.stringify({ event_id: 'current-event' }) },
  querySelector(selector) { return selector === '[data-sync-status]' ? status : retry; },
  closest() { return card; },
};
let flushed = false;
const window = {
  addEventListener() {},
  PolskiFlowResultQueue: { createQueue({ onStatus }) {
    return {
      async enqueue() {},
      async flushSession() {
        onStatus({ state: 'sent', eventId: 'older-event' });
        assert.equal(saved.hidden, true, 'Another queued result cannot schedule this lesson');
        assert.equal(pending.hidden, false);
        onStatus({ state: 'sent', eventId: 'current-event' });
        assert.equal(saved.hidden, false);
        assert.equal(pending.hidden, true);
        flushed = true;
      },
    };
  } },
};
const document = { querySelectorAll() { return []; }, addEventListener(name, callback) { handlers[name] = callback; } };
vm.runInNewContext(fs.readFileSync(__dirname + '/learning/static/polskiflow/lesson-result-sync.js', 'utf8'), { window, document });
handlers['htmx:afterSwap']({ target: { querySelectorAll() { return [panel]; } } });
setImmediate(() => { assert.equal(flushed, true, 'A swapped completion must initialize result syncing'); });
