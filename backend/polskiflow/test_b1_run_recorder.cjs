const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-run-recorder.js'), 'utf8');
class Element {
  constructor() { this.events = {}; this.dataset = {}; this.hidden = false; }
  addEventListener(name, callback) { (this.events[name] ||= []).push(callback); }
  emit(name, event = {}) { return this.events[name]?.reduce((_, callback) => callback(event), undefined); }
  dispatchEvent(event) { return this.emit(event.type, event); }
  pause() {} load() {} focus() {}
  removeAttribute(name) { delete this[name]; }
}
function fixture({denied = false, delayed = false, broken = false, preparing = false, mp4Only = false} = {}) {
  const nodes = Object.fromEntries(['start', 'stop', 'delete', 'audio', 'status', 'finish', 'restart', 'form', 'root', 'window', 'panel'].map(name => [name, new Element()]));
  if (preparing) nodes.root.dataset.preparingSpeaking = '1';
  nodes.panel.querySelector = selector => nodes[selector === 'audio' ? 'audio' : selector.match(/record-(.*?)\]/)[1]];
  nodes.root.querySelector = selector => nodes[selector.includes('finish') ? 'finish' : 'restart'];
  const track = new Element(); track.readyState = 'live'; track.stop = () => { track.readyState = 'ended'; };
  const stream = {getTracks: () => [track]};
  let calls = 0, resolvePermission, recording, revoked = [];
  class Recorder extends Element {
    static isTypeSupported(type) { return mp4Only ? type === 'audio/mp4' : type === 'audio/webm;codecs=opus'; }
    constructor(stream, options) { super(); if(mp4Only) assert.equal(options.mimeType, 'audio/mp4'); this.state = 'inactive'; this.mimeType = mp4Only ? 'audio/mp4' : 'audio/webm'; recording = this; }
    start() { if (broken) throw new Error('start failed'); this.state = 'recording'; }
    stop() { this.state = 'inactive'; }
    complete() { this.emit('dataavailable', {data: new Blob(['audio'])}); this.emit('stop'); }
  }
  vm.runInNewContext(source, {
    document: {querySelector: selector => nodes[selector.includes('recorder') ? 'panel' : 'root'], getElementById: () => nodes.form},
    navigator: {mediaDevices: {getUserMedia: () => { calls++; return denied ? Promise.reject(new Error('denied')) : delayed ? new Promise(resolve => { resolvePermission = resolve; }) : Promise.resolve(stream); }}},
    window: Object.assign(nodes.window, {MediaRecorder: Recorder}), MediaRecorder: Recorder, Blob,
    URL: {createObjectURL: blob => { assert.ok(blob.size > 0); return 'blob:local'; }, revokeObjectURL: url => revoked.push(url)},
  });
  return {nodes, track, calls: () => calls, recorder: () => recording, resolve: () => resolvePermission(stream), revoked};
}
(async () => {
  const safari = fixture({mp4Only: true});
  await safari.nodes.start.emit('click'); safari.nodes.stop.emit('click'); safari.recorder().complete();
  assert.equal(safari.recorder().mimeType, 'audio/mp4');
  assert.equal(safari.nodes.audio.hidden, false);
  const f = fixture(); assert.equal(f.calls(), 0, 'no automatic permission request');
  await f.nodes.start.emit('click'); assert.equal(f.track.readyState, 'live'); assert.equal(f.nodes.finish.disabled, true);
  f.nodes.stop.emit('click'); assert.equal(f.track.readyState, 'ended');
  assert.equal(f.nodes.start.disabled, true, 'wait for final chunks before another recording');
  await f.nodes.start.emit('click'); assert.equal(f.calls(), 1);
  f.recorder().complete(); assert.equal(f.nodes.audio.src, 'blob:local'); assert.equal(f.nodes.finish.disabled, false);
  f.nodes.delete.emit('click'); assert.equal(f.nodes.audio.hidden, true); assert.deepEqual(f.revoked, ['blob:local']);
  for (const event of ['b1-run-expired', 'pagehide', 'submit']) {
    const f = fixture(); await f.nodes.start.emit('click');
    f.nodes[event === 'pagehide' ? 'window' : event === 'submit' ? 'form' : 'root'].emit(event);
    assert.equal(f.track.readyState, 'ended'); f.recorder().complete();
    if (event !== 'b1-run-expired') assert.equal(f.nodes.audio.src, undefined);
    else assert.equal(f.nodes.finish.disabled, true);
  }
  for (const event of ['pagehide', 'b1-run-expired']) {
    const f = fixture({delayed: true}); const pending = f.nodes.start.emit('click');
    f.nodes[event === 'pagehide' ? 'window' : 'root'].emit(event); f.resolve(); await pending;
    assert.equal(f.track.readyState, 'ended'); assert.equal(f.recorder(), undefined);
  }
  for (const options of [{denied: true}, {broken: true}]) {
    const f = fixture(options); await f.nodes.start.emit('click');
    assert.equal(f.nodes.finish.disabled, false, 'self review remains available');
    if (options.broken) assert.equal(f.track.readyState, 'ended');
  }
  const preparing = fixture({preparing: true});
  assert.equal(preparing.nodes.start.disabled, true);
  await preparing.nodes.start.emit('click'); assert.equal(preparing.calls(), 0, 'preparation never requests microphone');
  const timer = new Element(), status = new Element(), tasks = [];
  const previousQuery = preparing.nodes.root.querySelector;
  preparing.nodes.root.querySelector = selector => selector.includes('prep-timer') ? timer : selector.includes('prep-status') ? status : previousQuery(selector);
  preparing.nodes.root.dataset.preparationSeconds = '120';
  let now = 100000;
  preparing.nodes.window.setTimeout = callback => tasks.push(callback);
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-run-speaking.js'), 'utf8'), {
    document: {querySelector: () => preparing.nodes.root}, window: preparing.nodes.window, Date: {now: () => now}, Event,
  });
  assert.equal(timer.textContent, '02:00');
  now += 30000; tasks[0](); assert.equal(timer.textContent, '01:30');
  now += 90000; tasks.at(-1)();
  assert.equal(timer.textContent, '00:00'); assert.equal(preparing.nodes.start.disabled, false); assert.equal(preparing.calls(), 0);
  await preparing.nodes.start.emit('click'); assert.equal(preparing.calls(), 1);
  preparing.nodes.window.emit('pagehide'); assert.equal(preparing.track.readyState, 'ended');
  const expiredPreparation = fixture({preparing: true});
  expiredPreparation.nodes.root.emit('b1-run-expired'); expiredPreparation.nodes.root.emit('b1-speaking-ready');
  assert.equal(expiredPreparation.nodes.finish.disabled, true, 'readiness cannot revive an expired part');
  console.log('Recording lifecycle: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
