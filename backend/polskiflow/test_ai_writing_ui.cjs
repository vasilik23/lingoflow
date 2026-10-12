const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path');
class Element extends EventTarget {
  constructor() {super(); this.value = ''; this.dataset = {}; this.checked = false; this.hidden = false; this.children = []; this.textContent = '';}
  replaceChildren() {this.children = [];}
  append(node) {this.children.push(node);}
}
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/ai-writing.js'), 'utf8');
function setup(language, speech = false) {
  const nodes = Object.fromEntries(['button', 'consent', 'status', 'result', 'editor', 'panel', 'window'].map(key => [key, new Element()]));
  nodes.editor.value = 'Mam problem';
  nodes.panel.dataset = {aiEditor: 'editor', aiUrl: '/review/', aiToken: 'fixture', ...(speech ? {aiSpeech: '1'} : {})};
  nodes.panel.querySelector = selector => ({'[data-ai-submit]': nodes.button, '[data-ai-consent]': nodes.consent, '[data-ai-confirmed]': nodes.consent, '[data-ai-status]': nodes.status, '[data-ai-result]': nodes.result})[selector];
  nodes.panel.closest = () => ({querySelectorAll: () => []});
  const requests = [];
  vm.runInNewContext(source, {
    document: {documentElement: {lang: language}, querySelectorAll: () => [nodes.panel], querySelector: () => ({value: 'csrf'}), getElementById: () => nodes.editor, createElement: () => new Element()},
    window: nodes.window, AbortController, setTimeout, clearTimeout,
    fetch(url, options) {return new Promise(resolve => requests.push({url, options, deliver(payload) {resolve({ok: true, json: async () => payload});}}));},
  });
  return {nodes, requests};
}
const result = {score: 12, maximum: 20, criteria: Object.fromEntries(['content', 'structure', 'grammar', 'vocabulary'].map(key => [key, {score: 3, feedback: 'fixture feedback'}])), errors: [{quote: '<img src=x>', correction: 'Mam pytanie', explanation: 'fixture explanation'}], next_step: 'fixture next step'};
const flush = () => new Promise(resolve => setImmediate(resolve));
(async () => {
  for (const language of ['ru', 'pl', 'en']) for (const speech of [false, true]) {
    const {nodes: n, requests} = setup(language, speech);
    n.button.dispatchEvent(new Event('click')); assert.equal(requests.length, 0);
    n.consent.checked = true; n.button.dispatchEvent(new Event('click'));
    requests[0].deliver({result}); await flush();
    assert.equal(n.result.hidden, false); assert.equal(n.result.lang, language);
    const error = n.result.children.find(node => node.children.length);
    assert.equal(error.children[0].lang, 'pl');
    assert.equal(error.children[0].textContent, '<img src=x> → Mam pytanie', 'untrusted text stays text');
    n.consent.checked = false; n.consent.dispatchEvent(new Event('change'));
    assert.equal(n.result.hidden, true); assert.equal(n.result.children.length, 0);
    n.consent.checked = true; n.button.dispatchEvent(new Event('click'));
    n.consent.checked = false; n.consent.dispatchEvent(new Event('change'));
    assert.equal(requests[1].options.signal.aborted, true);
    requests[1].deliver({result}); await flush(); assert.equal(n.result.hidden, true);
    n.consent.checked = true; n.button.dispatchEvent(new Event('click'));
    n.editor.value = 'Changed'; n.editor.dispatchEvent(new Event('input'));
    requests[2].deliver({result}); await flush(); assert.equal(n.result.hidden, true);
    n.button.dispatchEvent(new Event('click'));
    n.window.dispatchEvent(new Event('pagehide'));
    assert.equal(requests[3].options.signal.aborted, true);
    requests[3].deliver({result}); await flush(); assert.equal(n.result.hidden, true);
    assert.equal(n.editor.value, 'Changed', 'cancel does not delete the draft');
  }
  console.log('AI writing/transcript: consent revocation, stale response, pagehide, language and escaped correction PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
