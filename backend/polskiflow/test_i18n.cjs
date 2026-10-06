const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const directory = path.join(__dirname, 'learning/static/polskiflow');
function catalog(lang) {
  const window = {};
  const context = {window, document: {documentElement: {lang}}};
  vm.runInNewContext(fs.readFileSync(path.join(directory, 'i18n-pl.js'), 'utf8'), context);
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
