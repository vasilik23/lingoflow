const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const template = fs.readFileSync(path.join(__dirname, '../templates/reading/reader.html'), 'utf8');
const source = template.split('{% block scripts %}')[1].match(/<script>([\s\S]*?)<\/script>/)[1];
const element = () => ({disabled: false, textContent: '', value: '1', events: {}, addEventListener(event, fn) {this.events[event] = fn;}});
const controls = Object.fromEntries(['play', 'pause', 'stop', 'rate', 'status'].map(name => [name, element()]));
const panel = {hidden: true, querySelector(selector) {return controls[selector.match(/data-audio-(\w+)/)[1]];}};
const word = {...element(), dataset: {word: 'dom', lemma: 'dom', translation: 'дом', translationLang: 'ru', sourceTranslation: 'дом'}, classList: {add() {}}, closest: () => ({textContent: 'Mój dom.'})};
const fields = Object.fromEntries(['.word-panel-placeholder', '.word-panel-result', '#selected-word', '#selected-translation', '#word-input', '#translation-input', '#context-input'].map(key => [key, element()]));
const windowEvents = {}, spoken = [];
const wordHome = {append(panel) {panel.parentElement = this;}};
const wordPanel = {...element(), parentElement: wordHome};
const wordDialog = {...element(), open: false, append(panel) {panel.parentElement = this;}, showModal() {this.open = true;}, close() {this.open = false; this.events.close();}, getBoundingClientRect() {return {left: 20, right: 380, top: 500, bottom: 800};}};
fields['#word-panel'] = wordPanel;
fields['#word-dialog'] = wordDialog;
fields['[data-word-close]'] = element();
let returnedFocus = 0;
word.focus = (options) => {assert.equal(options.preventScroll, true); returnedFocus++;};
const speechSynthesis = {paused: false, cancel() {}, resume() {this.paused = false;}, pause() {this.paused = true;}, speak(utterance) {spoken.push(utterance);}};
const browserWindow = {speechSynthesis, SpeechSynthesisUtterance: function () {}, innerWidth: 1200, addEventListener(event, fn) {windowEvents[event] = fn;}};
vm.runInNewContext(source, {
  document: {querySelector(selector) {return selector === '[data-reading-audio]' ? panel : selector === '#reading-audio-text' ? {textContent: '["Mój dom."]'} : fields[selector] || null;}, querySelectorAll(selector) {return selector === '.reader-word' ? [word] : [];}},
  window: browserWindow,
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
for (const [lang, translation] of [['pl', 'dom'], ['en', 'house'], ['ru', 'дом']]) {
  word.dataset.translationLang = lang;
  word.dataset.translation = translation;
  word.events.click();
  assert.equal(fields['#selected-translation'].lang, lang, 'the panel updates the language for every selection');
  assert.equal(fields['#selected-translation'].textContent, translation);
  assert.equal(fields['#translation-input'].value, 'дом', 'localized display must not change the canonical saved value');
}
console.log('Reader speech cancellation, stale callbacks, pagehide and word selection: PASS');

// Mobile translation must keep the canonical form and restore the reading focus.
browserWindow.innerWidth = 393;
word.events.click();
assert.equal(wordDialog.open, true);
assert.equal(wordPanel.parentElement, wordDialog);
assert.equal(fields['#translation-input'].value, 'дом');
fields['[data-word-close]'].events.click();
assert.equal(wordDialog.open, false);
assert.equal(wordPanel.parentElement, wordHome);
assert.equal(returnedFocus, 1);
word.events.click();
browserWindow.innerWidth = 1440;
windowEvents.resize();
assert.equal(wordDialog.open, false);
assert.equal(wordPanel.parentElement, wordHome);
browserWindow.innerWidth = 393;
word.events.click();
wordDialog.events.click({target: wordDialog, clientX: 2, clientY: 2});
assert.equal(wordDialog.open, false);
assert.equal(returnedFocus, 3);
console.log('Mobile word translation, closing, focus restoration and desktop resize: PASS');

wordDialog.showModal = undefined;
let inlineFallback = 0;
wordPanel.scrollIntoView = (options) => {assert.equal(options.block, 'nearest'); inlineFallback++;};
word.events.click();
assert.equal(inlineFallback, 1, 'browsers without native dialogs keep the inline translation');
