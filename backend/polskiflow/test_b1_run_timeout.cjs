const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/b1-training-run.js'), 'utf8');
function page(mode = 'objective', fallback = false) {
  const inputs = [
    {name: 'answer_q1', value: '2', checked: true, matches: () => false},
    {name: 'answer_q2', value: '0', checked: false, matches: () => false},
    {name: 'answer_q3', value: '  czasu  ', matches: () => true, addEventListener() {}},
    {name: 'reviewed', value: 'on', checked: false, matches: () => false},
  ];
  const appended = [], events = {}, finish = {}, timer = {}, status = {}, storageStatus = {};
  let submissions = 0;
  const form = {querySelector: () => ({value: 'signed-token'}), querySelectorAll: () => inputs,
    addEventListener: (name, fn) => {events[name] = fn;}, appendChild: item => appended.push(item),
    submit() { submissions++; }};
  if (!fallback) form.requestSubmit = () => {events.submit?.(); submissions++;};
  const root = {dataset: {namespace: 'owner', phase: 'part', mode, seconds: '0'}, dispatchEvent() {},
    querySelector: selector => selector.includes('storage-status') ? storageStatus : selector.includes('timer-status') ? status : selector.includes('timer]') ? timer : selector.includes('finish-part') ? finish : selector.includes('restart') ? {addEventListener() {}} : null};
  const visibility = {};
  vm.runInNewContext(source, {document: {querySelector: () => root, getElementById: id => id === 'b1-run-form' ? form : null,
    createElement: () => ({}), addEventListener: (name, fn) => {visibility[name] = fn;}, hidden: false},
    sessionStorage: {getItem: () => null, setItem() {}, removeItem() {}}, URL, Date, Event,
    window: {location: {href: 'https://example.test/exam/b1/run/'}, addEventListener() {}, setTimeout() {throw Error('expired timer scheduled again');}, history: {replaceState() {}}, speechSynthesis: {cancel() {}}}, speechSynthesis: {cancel() {}}});
  visibility.visibilitychange();
  return {inputs, appended, finish, status, form, submissions};
}
for (const fallback of [false, true]) {
  const result = page('objective', fallback);
  assert.equal(result.submissions, 1);
  assert.equal(result.form.noValidate, true);
  assert.equal(result.finish.disabled, true);
  assert.equal(result.inputs[0].disabled, true);
  assert.equal(result.inputs[1].disabled, true);
  assert.deepEqual(result.appended.map(item => [item.name, item.value]), [['answer_q1', '2'], ['answer_q3', '  czasu  '], ['action', 'timeout']]);
}
const reviewed = page('self_review');
assert.equal(reviewed.submissions, 0);
assert.equal(reviewed.finish.disabled, false);
assert.equal(reviewed.inputs[3].disabled, false);
assert.match(reviewed.status.textContent, /самопроверку/);
console.log('Timeout freezes and submits selected/written answers once, bypasses required blanks; self-review is not graded: PASS');
