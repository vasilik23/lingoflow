const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
for (const template of ['base.html', 'offline.html']) {
  const source = fs.readFileSync(path.join(__dirname, '../templates', template), 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
  for (const [stored, system, expected] of [['light', true, 'light'], ['dark', false, 'dark'], [null, true, 'dark'], ['invalid', false, 'light']]) {
    const root = {dataset: {}, style: {}}, meta = {}, media = {matches: system, addEventListener() {}};
    const context = {document: {documentElement: root, querySelector: () => ({setAttribute: (name, value) => meta[name] = value})}, window: {matchMedia: () => media}, localStorage: {getItem: key => {assert.equal(key, 'polskiflow-theme'); return stored;}}};
    vm.runInNewContext(source, context);
    assert.equal(root.dataset.theme, expected, template + ' respects saved preference');
    assert.equal(meta.content, expected === 'dark' ? '#151518' : '#F7F7F9');
    context.window.PolskiFlowTheme.applyTheme(expected === 'dark' ? 'light' : 'dark');
    assert.equal(meta.content, expected === 'dark' ? '#F7F7F9' : '#151518', 'browser chrome follows theme switch');
  }
  const root = {dataset: {}, style: {}};
  vm.runInNewContext(source, {document: {documentElement: root, querySelector: () => null}, window: {matchMedia: () => ({matches: true, addEventListener() {}})}, localStorage: {getItem() {throw Error('blocked');}}});
  assert.equal(root.dataset.theme, 'dark', 'blocked storage falls back to system');
}
console.log('Main and offline theme metadata: saved choice, system fallback, blocked storage and switching PASS');
