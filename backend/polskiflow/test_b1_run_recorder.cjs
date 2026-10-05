const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-run-recorder.js'), 'utf8');
class Element {
  constructor() { this.events = {}; this.dataset = {}; this.hidden = false; }
  addEventListener(name, callback) { this.events[name] = callback; }
  emit(name, event = {}) { return this.events[name]?.(event); }
  pause() {} load() {} focus() {}
  removeAttribute(name) { delete this[name]; }
}
function fixture({denied = false, delayed = false, broken = false} = {}) {
  const nodes = Object.fromEntries(['start', 'stop', 'delete', 'audio', 'status', 'finish', 'restart', 'form', 'root', 'window', 'panel'].map(name => [name, new Element()]));
  nodes.panel.querySelector = selector => nodes[selector === 'audio' ? 'audio' : selector.match(/record-(.*?)\]/)[1]];
  nodes.root.querySelector = selector => nodes[selector.includes('finish') ? 'finish' : 'restart'];
  const track = new Element(); track.readyState = 'live'; track.stop = () => { track.readyState = 'ended'; };
  const stream = {getTracks: () => [track]};
  let calls = 0, resolvePermission, recording, revoked = [];
  class Recorder extends Element {
    constructor() { super(); this.state = 'inactive'; this.mimeType = 'audio/webm'; recording = this; }
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
  console.log('Recording lifecycle: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
