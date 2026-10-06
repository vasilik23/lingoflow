const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-run-listening.js'), 'utf8');
let now = 100000;
class Element {
  constructor() { this.events = {}; this.dataset = {namespace: 'owner', runId: 'run-one'}; }
  addEventListener(event, callback) { (this.events[event] ||= []).push(callback); }
  emit(event) { let result; for (const callback of this.events[event] || []) result = callback(); return result; }
}
function page(storage = new Map(), {runId = 'run-one', failStorage = false, unavailable = false, recorded = false} = {}) {
  const root = new Element(), play = new Element(), stop = new Element(), status = new Element(), form = new Element(), window = new Element();
  root.dataset.runId = runId;
  const audio = recorded ? new Element() : null;
  if (audio) Object.assign(audio, {plays: 0, pauses: 0, currentTime: 0, play() { this.plays++; }, pause() { this.pauses++; }});
  root.querySelector = selector => selector === 'audio[data-run-audio]' ? audio : selector.includes('audio-stop') ? stop : selector.includes('audio-status') ? status : play;
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
  return {root, play, stop, status, form, window, audio, spoken, tasks, cancels: () => cancels, state: () => JSON.parse([...storage.values()][0])};
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

const recordedStorage = new Map();
f = page(recordedStorage, {recorded: true, unavailable: true});
assert.equal(f.audio.plays, 0, 'recorded audio has no autoplay');
f.play.emit('click'); assert.equal(f.audio.plays, 1); assert.equal(f.state().used, 0);
f.audio.emit('playing'); f.audio.emit('playing'); assert.equal(f.state().used, 1);
f.stop.emit('click'); assert.equal(f.audio.pauses, 1); assert.equal(f.audio.currentTime, 0);
f = page(recordedStorage, {recorded: true}); assert.equal(f.play.disabled, true);
now += 30000; f.play.emit('click'); f.audio.emit('playing'); f.audio.emit('ended');
assert.equal(f.state().used, 2);
f = page(recordedStorage, {recorded: true}); now += 30000; f.play.emit('click'); assert.equal(f.audio.plays, 0);
for (const event of ['b1-run-expired', 'pagehide', 'submit']) {
  f = page(new Map(), {recorded: true}); f.play.emit('click'); f.audio.emit('playing');
  (event === 'pagehide' ? f.window : event === 'submit' ? f.form : f.root).emit(event);
  assert.equal(f.audio.pauses, 1); assert.equal(f.play.disabled, true);
  f.audio.emit('ended'); assert.equal(f.play.disabled, true);
}
f = page(new Map(), {recorded: true}); f.play.emit('click'); f.audio.emit('error');
assert.equal(f.state().used, 0); assert.equal(f.play.disabled, false);
f.play.emit('click'); f.tasks.filter(t=>t.delay===10000).at(-1).callback();
assert.equal(f.audio.pauses, 2); assert.equal(f.state().used, 0);
f.play.emit('click'); f.audio.emit('playing'); f.audio.emit('error');
assert.equal(f.state().used, 1); assert.equal(f.play.disabled, true);
console.log('Recorded audio: plays, reload, errors, watchdog and cleanup PASS');
(async () => {
  let fixture = page(new Map(), {recorded: true});
  let rejectOld;
  fixture.audio.play = () => new Promise((_, reject) => { rejectOld = reject; });
  fixture.play.emit('click');
  fixture.stop.emit('click');
  fixture.audio.play = () => Promise.resolve();
  fixture.play.emit('click');
  rejectOld(new Error('old attempt aborted'));
  await Promise.resolve();
  assert.equal(fixture.audio.pauses, 1, 'late rejection cannot cancel the new attempt');
  fixture.audio.emit('playing'); assert.equal(fixture.state().used, 1);
  fixture = page(new Map(), {recorded: true});
  fixture.audio.play = () => Promise.reject(new Error('network'));
  fixture.play.emit('click'); await Promise.resolve();
  assert.equal(fixture.state().used, 0); assert.equal(fixture.play.disabled, false);
  assert.equal(fixture.audio.pauses, 1);
  console.log('Recorded audio promise rejection and stale attempt: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });

function multiPage(storage = new Map()) {
  const main = new Element(), form = new Element(), win = new Element(); main.dataset.multiListening = '1';
  const players = ['variant', 'station'].map(id => {
    const root = new Element(), play = new Element(), stop = new Element(), status = new Element(), audio = new Element();
    root.dataset.blockId = id;
    Object.assign(audio, {pauses: 0, currentTime: 0, play() {}, pause() {this.pauses++;}});
    root.querySelector = selector => selector === 'audio[data-run-audio]' ? audio : selector.includes('audio-stop') ? stop : selector.includes('audio-status') ? status : play;
    return {root, play, stop, status, audio};
  });
  vm.runInNewContext(source, {
    document: {querySelector: () => main, querySelectorAll: () => players.map(p => p.root), getElementById: () => form}, window: win,
    Date: {now: () => now}, sessionStorage: {getItem: key => storage.get(key), setItem: (key,value) => storage.set(key,value)},
    setTimeout: () => 1, clearTimeout() {},
  });
  return {main, form, players, storage};
}
now = 100000; const multiStore = new Map(); let multi = multiPage(multiStore);
multi.players[0].play.emit('click'); multi.players[0].audio.emit('playing');
multi.players[1].play.emit('click'); assert.ok(multi.players[0].audio.pauses > 0, 'only one block plays at a time');
multi.players[1].audio.emit('playing'); multi.players[1].audio.emit('ended');
assert.equal(multiStore.size, 2, 'independent counter keys');
multi = multiPage(multiStore); assert.ok(multi.players.every(p => p.play.disabled), 'reload retains both cooldowns');
now += 30001; multi = multiPage(multiStore); multi.players[0].play.emit('click'); multi.players[0].audio.emit('playing'); multi.players[0].audio.emit('ended');
assert.equal(JSON.parse(multiStore.get('polskiflow-b1-run-listening:owner:variant')).used, 2);
assert.equal(JSON.parse(multiStore.get('polskiflow-b1-run-listening:owner:station')).used, 1);
multi.main.emit('b1-run-expired'); assert.ok(multi.players.every(p => p.play.disabled), 'main timer disables all blocks');
console.log('Multi-block counters, cooldown restore, exclusive playback and common deadline: PASS');
