const {test} = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const {harness, button, deferred, flush, text} = require('./component-harness.cjs');
const filename = path.join(__dirname, '../src/components/LessonScreen.tsx');
function fixture(steps) {
  const drafts = [], results = [], answers = [];
  const api = {
    loadLesson: async () => ({lesson: {id: 'lesson', title: 'Fixture lesson'}, steps}),
    saveLessonDraft(...args) {const wait = deferred(); drafts.push({args, ...wait}); return wait.promise;},
    saveLessonResult(...args) {const wait = deferred(); results.push({args, ...wait}); return wait.promise;},
    checkAnswer(...args) {const wait = deferred(); answers.push({args, ...wait}); return wait.promise;},
    deleteLessonDraft: async () => {},
  };
  const factory = harness(path.join(__dirname, '../src/lib/lesson-result.ts')).exports;
  const h = harness(filename, {'../lib/api': api, '../lib/lesson-result': factory});
  h.render({lessonId: 'lesson', stepIndex: 0, score: 0, session: {access_token: 'owner-token'}, colors: {}, onClose() {}}, h.exports.LessonScreen);
  return {h, drafts, results, answers};
}
const card = {position: 0, type: 'flashcard', polish: 'Dzień', translation: 'day'};
test('a failed draft save does not count the same flashcard twice', async () => {
  const {h, drafts} = fixture([card, {...card, position: 1}]); await flush(); h.render();
  button(h.tree, 'Знаю').onPress(); drafts[0].reject(Error('offline')); await flush(); h.render();
  button(h.tree, 'Знаю').onPress();
  assert.equal(drafts[1].args[2], 1);
  drafts[1].resolve({}); await flush(); h.render(); assert.match(text(h.tree), /2 \/ 2/);
});
test('rapid flashcard taps send one draft mutation and disable both choices', async () => {
  const {h, drafts} = fixture([card, {...card, position: 1}]); await flush(); h.render();
  const press = button(h.tree, 'Знаю').onPress; press(); press(); assert.equal(drafts.length, 1);
  h.render(); assert.equal(button(h.tree, 'Знаю').disabled, true); assert.equal(button(h.tree, 'Ещё учу').disabled, true);
  drafts[0].resolve({}); await flush();
});
test('rapid answer checks cannot inflate the score', async () => {
  const {h, answers, results} = fixture([{position: 0, type: 'choice', prompt: 'Choose', options: ['Tak', 'Nie']}]); await flush(); h.render();
  button(h.tree, 'Tak').onPress(); h.render(); const press = button(h.tree, 'Проверить').onPress;
  press(); press(); assert.equal(answers.length, 1);
  h.render(); assert.equal(button(h.tree, 'Nie').disabled, true);
  answers[0].resolve({correct: true, explanation: 'OK'}); await flush(); h.render();
  button(h.tree, 'Завершить').onPress();
  assert.equal(results[0].args[0].cards_known, 1); results[0].resolve({}); await flush();
});

test('lost completion ACK retries the entire immutable event and only celebrates after ACK', async () => {
  const {h, results} = fixture([card]); await flush(); h.render();
  const press = button(h.tree, 'Знаю').onPress; press(); press(); assert.equal(results.length, 1);
  const event = results[0].args[0]; assert.equal(event.cards_known, 1); assert(Object.isFrozen(event));
  h.render(); assert(!text(h.tree).includes('Урок завершён'));
  results[0].reject(Error('ACK lost')); await flush(); h.render();
  assert.match(text(h.tree), /Сохранение не подтверждено/);
  assert.throws(() => button(h.tree, 'Знаю'), /Missing button/);
  button(h.tree, 'Повторить сохранение').onPress();
  assert.equal(results[1].args[0], event, 'same ID, score and timestamp, not just a reused ID');
  assert.equal(results[1].args[1], 'owner-token');
  results[1].resolve({}); await flush(); h.render();
  assert.match(text(h.tree), /Урок завершён/); assert.match(text(h.tree), /1 из 1/);
});
