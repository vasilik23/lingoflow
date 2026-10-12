const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/listening-player.js'), 'utf8');
function setup({supported = true, throws = false} = {}) {
  const control = () => ({value: '1', disabled: true, textContent: '', events: {}, addEventListener(name, fn) {this.events[name] = fn;}});
  const players = {};
  for (const name of ['dialogue', 'b1', 'b2']) {
    const controls = Object.fromEntries(['play', 'repeat', 'rate', 'status', 'stop'].map(key => [key, control()]));
    const fragment = {...control(), dataset: {dialogueFragment: '0'}};
    players[name] = {controls, fragment, hidden: true,
      querySelector(selector) {return controls[selector.match(/-(play|repeat|rate|status|stop)/)[1]];},
      querySelectorAll(selector) {if (selector === '[data-dialogue-fragment]') return name === 'dialogue' ? [fragment] : []; return Object.values(controls).filter(c => c !== controls.status);}
    };
  }
  let prepared, cancelled = 0;
  const spoken = [], timers = new Map(), events = {};
  const synth = {cancel() {cancelled++;}, speak(utterance) {
    assert.equal(prepared, utterance, 'prepare synchronously before speak');
    if (throws) throw Error('unavailable');
    spoken.push(utterance);
  }};
  const window = {PolskiFlowAudioSession: {prepareSpeech(u) {prepared = u;}}, addEventListener(name, fn) {events[name] = fn;}};
  if (supported) Object.assign(window, {speechSynthesis: synth, SpeechSynthesisUtterance: function () {}});
  let timerId = 0;
  vm.runInNewContext(source, {
    document: {querySelector(selector) {return players[selector.match(/data-(dialogue|b1|b2)-player/)[1]];}, getElementById() {return {textContent: '["Dzień dobry.","Do widzenia."]'};}},
    window, speechSynthesis: synth, SpeechSynthesisUtterance: function(text) {this.text = text;},
    setTimeout(fn) {const id = ++timerId; timers.set(id, fn); return id;}, clearTimeout(id) {timers.delete(id);},
  });
  return {players, spoken, timers, events, cancelled: () => cancelled};
}
const f = setup();
for (const player of Object.values(f.players)) {
  assert.equal(player.hidden, false);
  player.controls.play.events.click();
  const u = f.spoken.at(-1);
  assert.equal(u.lang, 'pl-PL');
  assert.equal(player.controls.status.textContent, 'Подготавливаем системный польский голос…', 'tap alone does not prove playback');
  assert.equal(player.controls.stop.disabled, false);
  u.onstart();
  assert.equal(f.timers.size, 0);
  assert.match(player.controls.status.textContent, /^Воспроизведение/);
  u.onend();
  assert.equal(player.controls.stop.disabled, true);
  assert.match(player.controls.status.textContent, /прослушан/i);
}
const a = f.players.dialogue.controls, b = f.players.b1.controls;
a.play.events.click();
const stale = f.spoken.at(-1), staleStart = stale.onstart, staleEnd = stale.onend, staleError = stale.onerror;
b.play.events.click();
staleStart(); staleEnd(); staleError();
assert.equal(a.status.textContent, 'Воспроизведение остановлено');
assert.equal(b.status.textContent, 'Подготавливаем системный польский голос…');
const active = f.spoken.at(-1), lateEnd = active.onend;
b.stop.events.click(); lateEnd();
assert.equal(b.status.textContent, 'Воспроизведение остановлено');
assert.equal(f.timers.size, 0);
a.play.events.click();
[...f.timers.values()][0]();
assert.equal(a.status.textContent, 'Не удалось запустить системный польский голос');
assert.equal(a.stop.disabled, true);
a.repeat.events.click();
assert.equal(f.spoken.at(-1).text, 'Dzień dobry. Do widzenia.');
f.players.dialogue.fragment.events.click();
assert.equal(f.spoken.at(-1).text, 'Dzień dobry.');
const beforeHide = f.spoken.at(-1).onend;
f.events.pagehide(); beforeHide();
for (const player of Object.values(f.players)) {
  assert.equal(player.controls.status.textContent, 'Готово к воспроизведению');
  assert.equal(player.controls.stop.disabled, true);
}
assert.equal(f.timers.size, 0);
const missing = setup({supported: false});
assert.equal(missing.players.dialogue.hidden, false);
assert.equal(missing.players.dialogue.controls.play.disabled, true);
assert.equal(missing.players.dialogue.controls.status.textContent, 'Не удалось запустить системный польский голос');
const broken = setup({throws: true});
broken.players.b2.controls.play.events.click();
assert.equal(broken.players.b2.controls.status.textContent, 'Не удалось запустить системный польский голос');
assert.equal(broken.timers.size, 0);
console.log('Listening playback states, timeout, cancellation, stop, fragments, pagehide and unsupported API: PASS');
