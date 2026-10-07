const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../templates/b1_weekly_mock.html'), 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const storage = new Map();
let now = 1000000;
let failStorage = false;
function page({variant = 'v1', completed = false, restart = false, error = false} = {}) {
  const events = {}, tasks = [];
  const answers = [{name: 'answer_q1', value: '0'}, {name: 'answer_q1', value: '1'}];
  const token = {value: `token-${now}`};
  const clearButton = {addEventListener: (name, fn) => {events.clear = fn;}};
  const status = {};
  const announcements = [];
  const expiredEvents = [];
  const timerStatus = {set textContent(value) {announcements.push(value);}};
  const writing = {value: '', focus() {}, addEventListener: (name, fn) => {events[name] = fn;}};
  const timer = {parentElement: {classList: {add() {}}}};
  const form = {querySelector: () => token, querySelectorAll: () => answers,
    addEventListener: (name, fn) => {events[name] = fn;}, appendChild: input => {form.resume = input;}, submit: () => {form.submitted = true;}};
  vm.runInNewContext(source, {
    document: {querySelector: () => ({dispatchEvent: event => expiredEvents.push(event.type), dataset: {storageNamespace: 'owner', variantId: variant, durationSeconds: '900', ...(completed ? {completed: 'true'} : {}), ...(error ? {error: 'true'} : {})}}),
      getElementById: id => ({'mock-form': form, 'mock-writing': writing, 'mock-timer': timer, 'mock-clear-writing': clearButton, 'mock-draft-status': status, 'mock-timer-status': timerStatus}[id] || null), createElement: () => ({})},
    sessionStorage: {getItem: key => storage.get(key) || null, setItem: (key, value) => {if (failStorage) throw Error("quota"); storage.set(key, value);}, removeItem: key => storage.delete(key)},
    Date: {now: () => now}, Event, URL,
    window: {addEventListener: (name, fn) => {events[name] = fn;}, location: {href: `https://example.test/mock/${restart ? '?restart=1' : ''}`}, history: {replaceState() {}}, setTimeout: fn => tasks.push(fn)},
  });
  return {expiredEvents, announcements, status, answers, token, writing, timer, form, events, tasks};
}
let first = page();
const originalToken = first.token.value;
first.answers[1].checked = true; first.events.change();
first.writing.value = 'Mój tekst'; first.events.input();
now += 10000;
let resumed = page();
assert.equal(resumed.answers[1].checked, true);
assert.equal(resumed.writing.value, 'Mój tekst');
assert.equal(resumed.token.value, originalToken);
assert.equal(resumed.timer.textContent, '14:50');
now += 30000; resumed.tasks[0]();
assert.equal(resumed.timer.textContent, '14:20');
const changedWeek = page({variant: 'v2'});
assert.equal(changedWeek.form.submitted, true);
assert.equal(changedWeek.form.resume.name, 'resume');
assert.equal(changedWeek.token.value, originalToken);
assert.ok(changedWeek.answers.every(input => input.disabled));
resumed = page({restart: true});
assert.equal(resumed.answers.some(input => input.checked), false);
assert.equal(resumed.writing.value, '');
assert.notEqual(resumed.token.value, originalToken);
page({completed: true}); assert.equal(storage.size, 0);
storage.set('polskiflow-b1-mock:owner', '{broken');
assert.equal(page().timer.textContent, '15:00');
page({error: true}); assert.equal(storage.size, 0);
console.log('Weekly B1 resume: draft, token, timer, week change, reset and damaged storage passed');

const protectedPage = page({restart: true});
protectedPage.writing.value = 'Tekst'; protectedPage.events.input();
let prevented = false;
const event = {preventDefault() {prevented = true;}};
protectedPage.events.beforeunload(event); assert.equal(prevented, false);
failStorage = true;
protectedPage.writing.value += ' nowy'; protectedPage.events.input();
assert.match(protectedPage.status.textContent, /nie|не смог/);
protectedPage.events.beforeunload(event); assert.equal(prevented, true);
failStorage = false;
protectedPage.events.clear();
assert.equal(protectedPage.writing.value, '');
assert.equal(page({}).writing.value, '');
console.log('Writing deletion and storage-failure guard passed');

const checkpoints = page({restart: true});
assert.deepEqual(checkpoints.announcements, []);
now += 300000; checkpoints.tasks[0]();
assert.deepEqual(checkpoints.announcements, ['Осталось 10 минут.']);
now += 1000; checkpoints.tasks[1]();
assert.equal(checkpoints.announcements.length, 1);
now += 299000; checkpoints.tasks[2]();
assert.equal(checkpoints.announcements.at(-1), 'Осталось 5 минут.');
now += 240000; checkpoints.tasks[3]();
assert.equal(checkpoints.announcements.at(-1), 'Осталась одна минута.');
now += 60000; checkpoints.tasks[4]();
assert.equal(checkpoints.announcements.at(-1), 'Время истекло.');
assert.equal(checkpoints.announcements.length, 4);
assert.deepEqual(checkpoints.expiredEvents, ['b1-run-expired'], 'timer must stop the shared listening controller');
assert.ok(!fs.readFileSync(path.join(__dirname, '../templates/b1_weekly_mock.html'), 'utf8').includes('<main'));
console.log('Timer announces checkpoints only');
