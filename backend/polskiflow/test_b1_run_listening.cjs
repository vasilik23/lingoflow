const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-run-listening.js'), 'utf8');
let now = 100000;
class Element {
  constructor() { this.events = {}; this.dataset = {namespace: 'owner', runId: 'run-one'}; }
  addEventListener(event, callback) { this.events[event] = callback; }
  emit(event) { return this.events[event]?.(); }
}
function page(storage = new Map(), {runId = 'run-one', failStorage = false, unavailable = false} = {}) {
  const root = new Element(), play = new Element(), stop = new Element(), status = new Element(), form = new Element(), window = new Element();
  root.dataset.runId = runId;
  root.querySelector = selector => selector.includes('audio-stop') ? stop : selector.includes('audio-status') ? status : play;
  let spoken = [], cancels = 0;
  const tasks = [];
  const synthesis = {speak: utterance => spoken.push(utterance), cancel: () => {cancels++;}};
  if (!unavailable) Object.assign(window, {speechSynthesis: synthesis, SpeechSynthesisUtterance: function(text) {this.text = text;}});
  vm.runInNewContext(source, {
    document: {querySelector: () => root, getElementById: id => id === 'b1-run-form' ? form : {textContent: '"Polski komunikat"'}},
    window, speechSynthesis: synthesis, SpeechSynthesisUtterance: window.SpeechSynthesisUtterance,
    Date: {now: () => now},
    sessionStorage: {getItem: key => storage.get(key), setItem: (key, value) => {if (failStorage) throw Error('quota'); storage.set(key, value);}},
    setTimeout: (callback, delay) => {const task = {callback, delay, cancelled: false}; tasks.push(task); return task;}, clearTimeout: task => {if (task) task.cancelled = true;},
  });
  return {root, play, stop, status, form, window, spoken, tasks, cancels: () => cancels, state: () => JSON.parse([...storage.values()][0])};
}
const storage = new Map();
let f = page(storage);
assert.equal(f.spoken.length, 0, 'no autoplay');
f.play.emit('click'); f.play.emit('click'); assert.equal(f.spoken.length, 1, 'ignore duplicate starts');
assert.equal(f.state().used, 0, 'only actual start consumes a play');
f.spoken[0].onstart(); f.spoken[0].onstart(); assert.equal(f.state().used, 1);
f.spoken[0].onend(); assert.equal(f.play.disabled, true);
f = page(storage); f.play.emit('click'); assert.equal(f.spoken.length, 0, 'reload preserves pause');
now += 30000; f.play.emit('click'); f.spoken[0].onstart(); f.stop.emit('click');
assert.equal(f.state().used, 2); assert.equal(f.cancels(), 1);
f = page(storage); now += 30000; f.play.emit('click'); assert.equal(f.spoken.length, 0, 'two-play limit survives reload');
f = page(storage, {runId: 'new-run'}); assert.equal(f.state().used, 0, 'new run resets count');
f.play.emit('click'); f.spoken[0].onerror(); assert.equal(f.state().used, 0); assert.equal(f.play.disabled, false);
f.play.emit('click'); f.tasks.filter(t=>t.delay===10000).at(-1).callback(); assert.equal(f.play.disabled, false, 'missing start has watchdog');
for (const event of ['b1-run-expired', 'pagehide', 'submit']) {
  f = page(); f.play.emit('click'); f.spoken[0].onstart();
  (event === 'pagehide' ? f.window : event === 'submit' ? f.form : f.root).emit(event);
  assert.equal(f.cancels(), 1); assert.equal(f.play.disabled, true);
  f.spoken[0].onend(); assert.equal(f.play.disabled, true, 'late event cannot enable playback');
}
f = page(new Map(), {failStorage: true}); f.play.emit('click'); f.spoken[0].onstart(); f.spoken[0].onend();
assert.match(f.status.textContent, /не сохранится/);
f = page(new Map(), {unavailable: true}); f.play.emit('click'); assert.match(f.status.textContent, /недоступен/);
console.log('B1 listening limits, pauses, resume and cancellation: PASS');
