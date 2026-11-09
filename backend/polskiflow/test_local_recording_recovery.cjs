const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const template = fs.readFileSync(path.join(__dirname, '../templates/interaction.html'), 'utf8');
const source = [...template.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1]
  .replaceAll('{{ request.supabase_user.id|escapejs }}', 'fixture-owner');
class Element {
  constructor() { this.children = []; this.hidden = false; this.textContent = ''; this.events = {}; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute() {}
  addEventListener(name, fn) { this.events[name] = fn; }
}
const flush = () => new Promise(resolve => setImmediate(resolve));
async function setup(initial, denied = false) {
  const rows = new Map(initial.map(item => [item.id, item]));
  const list = new Element(), empty = new Element(), warning = new Element();
  warning.hidden = true;
  empty.textContent = 'Сохранённых записей пока нет.';
  function request(result, error) {
    const handlers = {};
    const value = {result, error, addEventListener(name, fn) { handlers[name] = fn; }};
    queueMicrotask(() => handlers[error ? 'error' : 'success']?.());
    return value;
  }
  const database = {transaction() { return {objectStore() { return {
    getAll() { return request([...rows.values()]); },
    delete(id) { rows.delete(id); return request(); },
  }; }}; }};
  const document = {documentElement: {lang: 'ru'}, querySelectorAll: () => [],
    querySelector(selector) { return {'[data-speaking-history-list]': list,
      '[data-speaking-history-empty]': empty, '[data-speaking-history-warning]': warning}[selector]; },
    createElement: () => new Element()};
  const indexedDB = {open() { return request(database, denied ? new Error('unavailable') : null); }};
  vm.runInNewContext(source, {document, indexedDB, Blob,
    window: {indexedDB, addEventListener() {}, confirm: () => true},
    URL: {createObjectURL(blob) { assert(blob instanceof Blob); return 'blob:fixture'; }, revokeObjectURL() {}}});
  await flush();
  return {list, empty, warning, rows};
}
const valid = (id, time) => ({id, owner: 'fixture-owner', title: id, createdAt: time,
  blob: new Blob(['synthetic audio'], {type: 'audio/wav'})});
(async () => {
  const broken = {...valid('broken', 300), blob: 'old-invalid-blob'};
  const foreign = {...broken, id: 'foreign', owner: 'other-owner'};
  let state = await setup([valid('older', 100), broken, valid('newer', 200), foreign]);
  assert.deepEqual(state.list.children.map(row => row.children[0].textContent), ['newer', 'older']);
  assert.equal(state.warning.hidden, false);
  assert.equal(state.empty.hidden, true);
  assert.equal(state.rows.size, 4, 'recovery never deletes malformed or foreign records');
  await state.list.children[0].children[3].events.click();
  await flush();
  assert.deepEqual([...state.rows.keys()].sort(), ['broken', 'foreign', 'older']);
  assert.equal(state.list.children.length, 1, 'explicit deletion removes only the selected valid recording');
  state = await setup([broken, foreign]);
  assert.equal(state.warning.hidden, false);
  assert.equal(state.empty.hidden, false);
  assert.equal(state.rows.size, 2);
  state = await setup([foreign]);
  assert.equal(state.warning.hidden, true, 'another owner cannot trigger a recovery warning');
  assert.equal(state.empty.hidden, false);
  state = await setup([valid('kept', 100)], true);
  assert.equal(state.list.children.length, 0);
  assert.equal(state.warning.hidden, true);
  assert.equal(state.empty.textContent, 'Локальная история недоступна в этом браузере.');
  for (const change of [{blob: new Blob([])}, {createdAt: NaN}, {createdAt: 1e30}, {title: null}]) {
    state = await setup([{...valid('invalid', 100), ...change}, valid('valid', 200)]);
    assert.equal(state.list.children.length, 1);
    assert.equal(state.warning.hidden, false);
    assert.equal(state.rows.size, 2);
  }
  console.log('Local recording recovery and owner isolation: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
