const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-training-run.js'), 'utf8');
const storage = new Map();
function page({normalize = false, fresh = false, failStorage = false, tokenValue = 'signed-part-token', withWriting = false} = {}) {
  const token = {value: tokenValue}, status = {hidden: true};
  const answer = {name: 'answer_tg07', value: '1', checked: false};
  const events = {}; let replacement = null;
  const editor = () => ({value: '', events: {}, addEventListener(name, callback) {this.events[name] = callback;}, focus() {}, dispatchEvent(event) {this.events[event.type]?.();}});
  const writing = editor(), writing2 = editor();
  const form = {querySelector: () => token, querySelectorAll: () => [answer], addEventListener: (event, callback) => {events[event] = callback;}, appendChild: input => {form.actionInput = input;}, submit: () => {form.submitted = true;}};
  const root = {dataset: {namespace: 'owner', phase: 'part', ...(normalize ? {normalizeNavigation: '1'} : {}), ...(fresh ? {fresh: '1'} : {})}, querySelector: selector => selector.includes('storage-status') ? status : selector.includes('clear-run-writing') && withWriting ? {addEventListener(name, callback) {events[selector] = callback;}} : selector.includes('restart') ? {addEventListener() {}} : null};
  vm.runInNewContext(source, {
    document: {querySelector: () => root, getElementById: id => id === 'b1-run-form' ? form : withWriting && id === 'run-writing' ? writing : withWriting && id === 'run-writing-2' ? writing2 : null, createElement: () => ({})},
    sessionStorage: {getItem: key => storage.get(key), setItem: (key, value) => {if (failStorage) throw Error('quota'); storage.set(key, value);}, removeItem: key => storage.delete(key)},
    URL, Date, Event,
    window: {location: {href: 'https://example.test/exam/b1/run/', replace: url => {replacement = String(url);}}, addEventListener(name, callback) {events[name] = callback;}, history: {replaceState() {}}},
  });
  return {token, answer, form, events, status, replacement, writing, writing2};
}
let f = page({normalize: true});
assert.equal(f.replacement, 'https://example.test/exam/b1/run/');
assert.equal(JSON.parse([...storage.values()][0]).token, 'signed-part-token', 'save before GET navigation');
f = page({fresh: true, tokenValue: 'new-intro-token'});
assert.equal(f.form.submitted, true); assert.equal(f.form.actionInput.value, 'resume'); assert.equal(f.token.value, 'signed-part-token');
f = page(); f.answer.checked = true; f.events.change();
f = page(); assert.equal(f.answer.checked, true, 'resume keeps answers for exact signed state');
f = page({normalize: true, failStorage: true});
assert.equal(f.replacement, null, 'never navigate away if new state could not be saved'); assert.equal(f.status.hidden, false);
console.log('B1 mutation navigation, resume and unavailable storage: PASS');

storage.clear();
f = page({withWriting: true});
f.writing.value = 'Krótki tekst'; f.writing.events.input();
f.writing2.value = 'Dłuższy tekst'; f.writing2.events.input();
f = page({withWriting: true});
assert.equal(f.writing.value, 'Krótki tekst'); assert.equal(f.writing2.value, 'Dłuższy tekst');
f.events['[data-clear-run-writing]']();
assert.equal(f.writing.value, ''); assert.equal(f.writing2.value, 'Dłuższy tekst');
f.events['[data-clear-run-writing2]'](); assert.equal(f.writing2.value, '');
f = page({withWriting: true, failStorage: true}); f.writing2.value = 'Nie zapisano'; f.writing2.events.input();
let prevented = false; f.events.beforeunload({preventDefault() {prevented = true;}}); assert.equal(prevented, true);
f = page({tokenValue: 'next-stage-token'});
const saved = JSON.parse([...storage.values()][0]); assert.equal(saved.writing, ''); assert.equal(saved.writing2, '');
console.log('Two independent writing drafts, deletion, cleanup and failed-storage guard: PASS');

const counters = [
  {dataset: {editor: 'short', minimum: '50', maximum: '80'}},
  {dataset: {editor: 'long', minimum: '140', maximum: '170'}},
];
const editors = Object.fromEntries(['short', 'long'].map(id => [id, {id: id === 'long' ? 'run-writing-2' : 'run-writing', value: '', addEventListener(name, callback) {this.update = callback;}}]));
vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-run-writing.js'), 'utf8'), {
  document: {querySelectorAll: () => counters, getElementById: id => editors[id], querySelector: () => null},
});
assert.match(counters[0].textContent, /Слов: 0/);
editors.short.value = 'słowo\n'.repeat(50); editors.short.update();
assert.match(counters[0].textContent, /Слов: 50.*в диапазоне/);
editors.long.value = 'zdanie '.repeat(171); editors.long.update();
assert.match(counters[1].textContent, /Слов: 171.*выше ориентира/);
editors.long.value = '  '; editors.long.update(); assert.match(counters[1].textContent, /Слов: 0/);
console.log('Independent word counts and editorial range boundaries: PASS');
