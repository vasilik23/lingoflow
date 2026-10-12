const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const template = fs.readFileSync(path.join(__dirname, '../templates/listening.html'), 'utf8');
const source = template.split('{% block scripts %}')[1].match(/<script>([\s\S]*?)<\/script>/)[1];
const control = () => ({value: '1', disabled: true, textContent: '', events: {}, addEventListener(name, fn) {this.events[name] = fn;}});
const players = {};
for (const name of ['dialogue', 'b1', 'b2']) {
  const controls = Object.fromEntries(['play', 'repeat', 'rate', 'status'].map(key => [key, control()]));
  players[name] = {controls, hidden: true, querySelector(selector) {return controls[selector.match(/-(play|repeat|rate|status)/)[1]];}, querySelectorAll() {return [];}};
}
let prepared, spoken;
const events = {};
const speechSynthesis = {cancel() {}, speak(utterance) {assert.equal(prepared, utterance, 'prepare playback synchronously before speaking'); spoken = utterance;}};
vm.runInNewContext(source, {
  document: {querySelector(selector) {
    const player = selector.match(/data-(dialogue|b1|b2)-player/);
    if (player) return players[player[1]];
    return {textContent: '["Dzień dobry."]'};
  }},
  window: {speechSynthesis, SpeechSynthesisUtterance: function () {}, PolskiFlowAudioSession: {prepareSpeech(utterance) {prepared = utterance;}}, addEventListener(name, fn) {events[name] = fn;}},
  speechSynthesis, SpeechSynthesisUtterance: function(text) {this.text = text;},
});
for (const player of Object.values(players)) {
  assert.equal(player.hidden, false);
  player.controls.play.events.click();
  assert.equal(spoken.lang, 'pl-PL');
  assert.equal(spoken.text, 'Dzień dobry.');
  player.controls.repeat.events.click();
  assert.equal(prepared, spoken);
}
console.log('Listening dialogue/B1/B2 synchronous playback preparation: PASS');
