const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../templates/b1_exam_simulation.html'), 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const local = new Map();
const session = new Map();
const storage = map => ({getItem: key => map.get(key) || null, setItem: (key, value) => map.set(key, value), removeItem: key => map.delete(key)});
let now = 1000000;
let failStorage = false;
function page({part = 'reading', restart = false, duration = 60, result} = {}) {
  const listeners = {};
  const answers = [{name: 'answer_q1', value: '0', checked: false}, {name: 'answer_q1', value: '1', checked: false}];
  const token = {value: 'new-token'};
  const form = {querySelector: () => token, addEventListener: (name, fn) => { listeners[name] = fn; }};
  const clearButton = {addEventListener: (name, fn) => {listeners.clear = fn;}};
  const status = {};
  const announcements = [];
  const timerStatus = {set textContent(value) {announcements.push(value);}};
  const writing = {value: '', focus() {}, addEventListener: (name, fn) => { listeners[name] = fn; }};
  const timer = {parentElement: {classList: {add() {}}}};
  const complete = {addEventListener: (name, fn) => { listeners.complete = fn; }};
  const root = {dataset: {storageNamespace: 'owner', variantId: 'v1', partId: part, timingMode: part === 'writing' ? 'full' : 'short', durationSeconds: String(duration), ...(result === undefined ? {} : {resultPercent: String(result)})}};
  const callbacks = [];
  vm.runInNewContext(source, {
    document: {
      querySelector: selector => selector === '[data-simulation-root]' ? root : complete,
      querySelectorAll: selector => selector.includes('radio') ? answers : [],
      getElementById: id => ({'simulation-form': form, 'simulation-writing': part === 'writing' ? writing : null, 'simulation-timer': timer, 'simulation-clear-writing': clearButton, 'simulation-draft-status': status, 'simulation-timer-status': timerStatus}[id] || null),
    },
    localStorage: storage(local), sessionStorage: {...storage(session), setItem: (key, value) => {if (failStorage) throw Error("quota"); session.set(key, value);}},
    Date: {now: () => now}, URL, URLSearchParams,
    window: {addEventListener: (name, fn) => {listeners[name] = fn;}, location: {search: restart ? '?restart=1' : '', href: 'https://example.test/?restart=1', assign() {}}, history: {replaceState() {}}, setTimeout: fn => callbacks.push(fn)},
  });
  return {announcements, status, answers, token, writing, timer, listeners, callbacks};
}
let first = page();
first.answers[1].checked = true;
first.listeners.change();
now += 10000;
let resumed = page();
assert.equal(resumed.answers[1].checked, true);
assert.equal(resumed.token.value, 'new-token');
assert.equal(resumed.timer.textContent, '00:50');
now += 30000;
resumed.callbacks[0]();
assert.equal(resumed.timer.textContent, '00:20', 'background delay uses elapsed wall time');
assert.equal(page({restart: true}).answers.some(input => input.checked), false);
first = page({part: 'writing'});
first.writing.value = 'Mój tekst';
first.listeners.input();
assert.equal(page({part: 'writing'}).writing.value, 'Mój tekst');
first.listeners.complete();
assert.equal(session.has('polskiflow-b1-simulation:owner:v1:full:writing:draft'), false);
page({result: 80});
assert.equal(session.has('polskiflow-b1-simulation:owner:v1:short:reading:draft'), false);
assert.equal(JSON.parse(local.get('polskiflow-b1-simulation:owner:v1:short:reading')).percent, 80);
console.log('B1 resume: answers, writing, restart, completion and elapsed timer passed');

const protectedPage = page({part: 'writing'});
protectedPage.writing.value = 'Tekst'; protectedPage.listeners.input();
let prevented = false;
const event = {preventDefault() {prevented = true;}};
protectedPage.listeners.beforeunload(event); assert.equal(prevented, false);
failStorage = true;
protectedPage.writing.value += ' nowy'; protectedPage.listeners.input();
assert.match(protectedPage.status.textContent, /nie|не смог/);
protectedPage.listeners.beforeunload(event); assert.equal(prevented, true);
failStorage = false;
protectedPage.listeners.clear();
assert.equal(protectedPage.writing.value, '');
assert.equal(page({part: 'writing'}).writing.value, '');
console.log('Writing deletion and storage-failure guard passed');

const checkpoints = page({restart: true, duration: 900});
assert.deepEqual(checkpoints.announcements, []);
now += 300000; checkpoints.callbacks[0]();
assert.deepEqual(checkpoints.announcements, ['Осталось 10 минут.']);
now += 1000; checkpoints.callbacks[1]();
assert.equal(checkpoints.announcements.length, 1);
now += 299000; checkpoints.callbacks[2]();
assert.equal(checkpoints.announcements.at(-1), 'Осталось 5 минут.');
now += 240000; checkpoints.callbacks[3]();
assert.equal(checkpoints.announcements.at(-1), 'Осталась одна минута.');
now += 60000; checkpoints.callbacks[4]();
assert.equal(checkpoints.announcements.at(-1), 'Время истекло.');
assert.equal(checkpoints.announcements.length, 4);
assert.ok(!fs.readFileSync(path.join(__dirname, '../templates/b1_exam_simulation.html'), 'utf8').includes('<main'));
console.log('Timer announces checkpoints only');
