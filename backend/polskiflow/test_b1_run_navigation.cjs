const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-training-run.js'), 'utf8');
const storage = new Map();
function page({normalize = false, fresh = false, failStorage = false, tokenValue = 'signed-part-token'} = {}) {
  const token = {value: tokenValue}, status = {hidden: true};
  const answer = {name: 'answer_tg07', value: '1', checked: false};
  const events = {}; let replacement = null;
  const form = {querySelector: () => token, querySelectorAll: () => [answer], addEventListener: (event, callback) => {events[event] = callback;}, appendChild: input => {form.actionInput = input;}, submit: () => {form.submitted = true;}};
  const root = {dataset: {namespace: 'owner', phase: 'part', ...(normalize ? {normalizeNavigation: '1'} : {}), ...(fresh ? {fresh: '1'} : {})}, querySelector: selector => selector.includes('storage-status') ? status : selector.includes('restart') ? {addEventListener() {}} : null};
  vm.runInNewContext(source, {
    document: {querySelector: () => root, getElementById: id => id === 'b1-run-form' ? form : null, createElement: () => ({})},
    sessionStorage: {getItem: key => storage.get(key), setItem: (key, value) => {if (failStorage) throw Error('quota'); storage.set(key, value);}, removeItem: key => storage.delete(key)},
    URL, Date,
    window: {location: {href: 'https://example.test/exam/b1/run/', replace: url => {replacement = String(url);}}, addEventListener() {}, history: {replaceState() {}}},
  });
  return {token, answer, form, events, status, replacement};
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
