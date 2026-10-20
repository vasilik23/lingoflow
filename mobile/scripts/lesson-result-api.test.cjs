const {test} = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const {harness} = require('./component-harness.cjs');
const {createLessonResult} = harness(path.join(__dirname, '../src/lib/lesson-result.ts')).exports;
test('result API requires a matching created/duplicate receipt', async () => {
  const event = createLessonResult('lesson', 3, 2, 'attempt-id'), calls = []; let reply;
  const {saveLessonResult} = harness(path.join(__dirname, '../src/lib/api.ts'), {'./config': {config: {apiBaseUrl: 'https://fixture.invalid'}}, $globals: {fetch: async (url, options) => {calls.push({url, options}); return {ok: true, json: async () => ({data: reply})};}}}).exports;
  for (const wrong of [null, {}, {event_id: 'other', status: 'created'}, {event_id: event.event_id, status: 'conflict'}]) {reply = wrong; await assert.rejects(saveLessonResult(event, 'owner-token'), /не подтвердил/);}
  for (const status of ['created', 'duplicate']) {reply = {event_id: event.event_id, status}; assert.equal((await saveLessonResult(event, 'owner-token')).status, status);}
  assert(calls.every(call => call.options.body === JSON.stringify(event)), 'every retry sends the same complete payload');
  assert(calls.every(call => call.options.headers.Authorization === 'Bearer owner-token'));
  assert.equal(event.plan_date, event.completed_at.slice(0, 10));
});
