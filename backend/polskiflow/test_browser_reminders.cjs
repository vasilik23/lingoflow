const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/browser-reminders.js'), 'utf8');
function fixture(options = {}) {
  const events = {}, documentEvents = {}, panel = {hidden: true}, storage = options.storage || new Map();
  const key = 'lingoflow-reminder:owner';
  if (!storage.has(key)) storage.set(key, JSON.stringify({enabled: options.enabled !== false}));
  let fetches = 0, permissions = 0, clock = 0;
  const data = {namespace: 'owner', day: '2026-10-16', due: true, channel: 'today_foreground', ...options.data};
  let interval;
  const dismiss = {addEventListener: (_, fn) => events.dismiss = fn};
  const root = {dataset: {namespace: 'owner', endpoint: '/session/reminder/'}, querySelector: s => s === '[data-reminder-panel]' ? panel : s === '[data-reminder-dismiss]' ? dismiss : null};
  const document = {visibilityState: options.hidden ? 'hidden' : 'visible', querySelector: () => root, addEventListener: (e, fn) => documentEvents[e] = fn};
  const context = {
    document, navigator: {locks: options.noLocks ? undefined : {request: async (_, __, fn) => fn({})}},
    localStorage: {getItem: k => {if (options.storageError) throw Error(); return storage.get(k) || null;}, setItem: (k, v) => {if(options.writeError) throw Error(); storage.set(k,v);}},
    window: {addEventListener: (e, fn) => events[e] = fn},
    performance: {now: () => clock}, AbortController,
    setTimeout: () => 1, clearTimeout() {}, setInterval: fn => interval = fn,
    fetch: async () => {fetches++; if(options.error) throw Error(); if(options.beforeResponse) await options.beforeResponse({document, events, storage, key}); if(options.stale) clock += 6000; return {ok: options.ok !== false, json: async () => data};},
    Notification: {requestPermission: () => permissions++},
  };
  vm.runInNewContext(source, context);
  return {panel, storage, events, documentEvents, document, tick: () => interval(), fetches: () => fetches, permissions: () => permissions};
}
const settle = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  let f = fixture(); await settle(); assert.equal(f.panel.hidden, false); assert.equal(f.permissions(), 0);
  f.events.dismiss(); await f.tick(); assert.equal(f.panel.hidden, true); // no repeat same day
  const second = fixture({storage:f.storage}); await settle(); assert.equal(second.panel.hidden, true);
  for (const options of [{enabled:false}, {hidden:true}, {noLocks:true}, {storageError:true}, {writeError:true}, {error:true}, {ok:false}, {stale:true}, {data:{due:false}}, {data:{namespace:'another-owner'}}, {data:{day:'bad'}}, {data:{channel:'push'}}]) {
    f = fixture(options); await settle(); assert.equal(f.panel.hidden,true, JSON.stringify(options));
  }
  for (const action of [({events}) => events.pagehide(), ({document}) => document.visibilityState='hidden', ({storage,key}) => storage.set(key,'{"enabled":false}')]) {
    f=fixture({beforeResponse:action}); await settle(); assert.equal(f.panel.hidden,true);
  }
  f=fixture(); await settle(); f.document.visibilityState='hidden'; f.documentEvents.visibilitychange(); assert.equal(f.panel.hidden,true);
  f=fixture(); await settle(); f.events.storage({key:null}); assert.equal(f.panel.hidden,true);
  console.log('Browser reminder consent, owner, deduplication, lifecycle and failure checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
