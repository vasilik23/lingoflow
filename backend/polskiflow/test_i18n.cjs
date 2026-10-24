const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const directory = path.join(__dirname, 'learning/static/polskiflow');
function catalog(lang) {
  const window = {};
  const context = {window, document: {documentElement: {lang}}};
  vm.runInNewContext(fs.readFileSync(path.join(directory, 'i18n-pl.js'), 'utf8'), context);
  vm.runInNewContext(fs.readFileSync(path.join(directory, 'i18n-en.js'), 'utf8'), context);
  vm.runInNewContext(fs.readFileSync(path.join(directory, 'i18n.js'), 'utf8'), context);
  return window.PolskiFlowI18n.t;
}
const pl = catalog('pl'), ru = catalog('ru');
assert.equal(pl('Словарь'), 'Słownik');
assert.equal(ru('Словарь'), 'Словарь');
assert.equal(pl`Слов: ${12} · ориентир ${50}–${80} · ${'minimum'}`, 'Słów: 12 · wskazówka 50–80 · minimum');
assert.equal(pl`Уникальный текст ${'<script>'}`, 'Уникальный текст <script>');
assert.equal(ru`Осталось ${3} минут.`, 'Осталось 3 минут.');
assert.equal(pl('окончания падежей'), 'końcówki przypadków');
console.log('Polish and Russian browser catalogues and interpolation: PASS');

const en = catalog('en');
assert.equal(en('Словарь'), 'Dictionary');
assert.equal(en`Слов: ${12} · ориентир ${50}–${80} · ${'minimum'}`, 'Words: 12 · target 50–80 · minimum');

// Exercise the actual compact assets as well as the legacy full catalogue.
const dynamic = JSON.parse(fs.readFileSync(path.join(__dirname, 'localization/browser_messages.json'), 'utf8'));
for (const lang of ['pl', 'en']) {
  const name = lang === 'pl' ? 'Polish' : 'English';
  const fullWindow = {}, runtimeWindow = {};
  vm.runInNewContext(fs.readFileSync(path.join(directory, `i18n-${lang}.js`), 'utf8'), {window: fullWindow});
  const context = {window: runtimeWindow, document: {documentElement: {lang}}};
  vm.runInNewContext(fs.readFileSync(path.join(directory, `i18n-runtime-${lang}.js`), 'utf8'), context);
  vm.runInNewContext(fs.readFileSync(path.join(directory, 'i18n.js'), 'utf8'), context);
  const full = fullWindow[`PolskiFlow${name}Messages`];
  const runtime = runtimeWindow[`PolskiFlow${name}Messages`];
  for (const key of new Set([...dynamic, ...Object.keys(full).filter(key => key.includes('%(v'))])) {
    assert.equal(runtime[key], full[key], `${lang}: ${key}`);
    assert.equal(runtimeWindow.PolskiFlowI18n.t(key), full[key]);
  }
  for (const [key,value] of Object.entries(runtime)) assert.equal(value,full[key]);
  const t = runtimeWindow.PolskiFlowI18n.t;
  assert.equal(t`Слов: ${12} · ориентир ${50}–${80} · ${'minimum'}`,
    lang === 'pl' ? 'Słów: 12 · wskazówka 50–80 · minimum' : 'Words: 12 · target 50–80 · minimum');
}
console.log('Runtime catalogues match gettext and preserve dynamic messages: PASS');
