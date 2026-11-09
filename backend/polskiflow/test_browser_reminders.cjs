const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/browser-reminders.js'), 'utf8');
function fixture(options = {}) {
  const events = {}, documentEvents = {}, panel = {hidden: true}, storage = options.storage || new Map();
  const key = 'lingoflow-reminder:owner';
  if (!storage.has(key)) storage.set(key, JSON.stringify({enabled: options.enabled !== false}));
  let fetches = 0, permissions = 0, clock = 0, lockDepth = 0;
  const writes = [];
  const data = {namespace: 'owner', day: '2026-10-16', due: true, channel: 'today_foreground', ...options.data};
  let interval;
  const dismiss = {addEventListener: (_, fn) => events.dismiss = fn};
  const toggle = options.toggle ? {addEventListener: (_, fn) => events.toggle = fn} : null;
  const status = {textContent: ''};
  const root = {dataset: {namespace: 'owner', endpoint: '/session/reminder/'}, querySelector: s => s === '[data-reminder-panel]' ? panel : s === '[data-reminder-dismiss]' ? dismiss : s === '[data-reminder-toggle]' ? toggle : s === '[data-reminder-status]' ? status : null};
  const document = {visibilityState: options.hidden ? 'hidden' : 'visible', querySelector: () => root, addEventListener: (e, fn) => documentEvents[e] = fn};
  const context = {
    document, navigator: {locks: options.noLocks ? undefined : {request: async (_, options, fn) => {
      lockDepth++; try { return await (fn || options)({}); } finally { lockDepth--; }
    }}},
    localStorage: {getItem: k => {if (options.storageError) throw Error(); const value = storage.get(k) || null; options.afterRead?.(k, storage); return value;}, setItem: (k, v) => {writes.push({key:k, locked:lockDepth>0}); if(options.writeError) throw Error(); storage.set(k,v);}},
    window: {addEventListener: (e, fn) => events[e] = fn},
    performance: {now: () => clock}, AbortController,
    setTimeout: () => 1, clearTimeout() {}, setInterval: fn => interval = fn,
    fetch: async () => {fetches++; if(options.error) throw Error(); if(options.beforeResponse) await options.beforeResponse({document, events, storage, key}); if(options.stale) clock += 6000; return {ok: options.ok !== false, json: async () => data};},
    Notification: {requestPermission: () => permissions++},
  };
  vm.runInNewContext(source, context);
  return {panel, storage, writes, events, documentEvents, document, tick: () => interval(), fetches: () => fetches, permissions: () => permissions};
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
  // Another tab may write between a capability read and its subsequent write.
  for (const updated of [{enabled: false}, {enabled: true, day: '2026-10-16'}]) {
    let reads = 0;
    f = fixture({toggle: true, afterRead(key, storage) {
      if (key === 'lingoflow-reminder:owner' && ++reads === 2) storage.set(key, JSON.stringify(updated));
    }});
    await settle();
    assert.equal(f.panel.hidden, true, 'capability checks must not erase another tab opt-out/day claim');
    assert.deepEqual(JSON.parse(f.storage.get('lingoflow-reminder:owner')), updated);
    assert(f.writes.every(write => write.locked), 'all preference writes use the cross-tab lock');
  }
  f = fixture({toggle: true}); await settle();
  await f.events.toggle();
  assert.equal(JSON.parse(f.storage.get('lingoflow-reminder:owner')).enabled, false);
  f = fixture({toggle: true, writeError: true}); await settle(); assert.equal(f.panel.hidden, true);
  console.log('Browser reminder consent, owner, deduplication, lifecycle and failure checks passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
