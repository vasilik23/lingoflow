const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const template = fs.readFileSync(path.join(__dirname, '../templates/reading/reader.html'), 'utf8');
const source = template.split('{% block scripts %}')[1].match(/<script>([\s\S]*?)<\/script>/)[1];
const element = () => ({disabled: false, textContent: '', value: '1', events: {}, addEventListener(event, fn) {this.events[event] = fn;}});
const controls = Object.fromEntries(['play', 'pause', 'stop', 'rate', 'status'].map(name => [name, element()]));
const panel = {hidden: true, querySelector(selector) {return controls[selector.match(/data-audio-(\w+)/)[1]];}};
const word = {...element(), dataset: {word: 'dom', lemma: 'dom', translation: 'дом', sourceTranslation: 'дом'}, classList: {add() {}}, closest: () => ({textContent: 'Mój dom.'})};
const fields = Object.fromEntries(['.word-panel-placeholder', '.word-panel-result', '#selected-word', '#selected-translation', '#word-input', '#translation-input', '#context-input'].map(key => [key, element()]));
const windowEvents = {}, spoken = [];
const speechSynthesis = {paused: false, cancel() {}, resume() {this.paused = false;}, pause() {this.paused = true;}, speak(utterance) {spoken.push(utterance);}};
vm.runInNewContext(source, {
  document: {querySelector(selector) {return selector === '[data-reading-audio]' ? panel : selector === '#reading-audio-text' ? {textContent: '["Mój dom."]'} : fields[selector] || null;}, querySelectorAll(selector) {return selector === '.reader-word' ? [word] : [];}},
  window: {speechSynthesis, SpeechSynthesisUtterance: function () {}, innerWidth: 1200, addEventListener(event, fn) {windowEvents[event] = fn;}},
  speechSynthesis, SpeechSynthesisUtterance: function (text) {this.text = text;},
});
controls.play.events.click();
const staleEnd = spoken[0].onend, staleError = spoken[0].onerror;
controls.play.events.click();
assert.equal(spoken[0].onend, null);
staleEnd(); staleError();
assert.equal(controls.pause.disabled, false, 'cancelled speech must not disable the new player');
assert.equal(controls.status.textContent, 'Воспроизведение');
const stoppedError = spoken[1].onerror;
controls.stop.events.click(); stoppedError();
assert.equal(controls.status.textContent, 'Воспроизведение остановлено', 'late error must not overwrite intentional stop');
controls.play.events.click(); spoken[2].onend();
assert.equal(controls.status.textContent, 'Текст прослушан');
controls.play.events.click(); windowEvents.pagehide();
assert.equal(controls.pause.disabled, true, 'back-forward cache restores a stopped player');
assert.equal(controls.status.textContent, 'Готово к воспроизведению');
word.events.click();
assert.equal(fields['#word-input'].value, 'dom', 'word selection tolerates an unrecognized word query status');
console.log('Reader speech cancellation, stale callbacks, pagehide and word selection: PASS');
