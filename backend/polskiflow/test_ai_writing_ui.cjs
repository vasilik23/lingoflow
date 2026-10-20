const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path');
class Element extends EventTarget {
  constructor() {super(); this.value = ''; this.dataset = {}; this.checked = false; this.hidden = false; this.children = []; this.textContent = '';}
  replaceChildren(...nodes) {this.children = nodes;}
  append(node) {this.children.push(node);}
}
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/ai-writing.js'), 'utf8');
function setup(language, speech = false) {
  const nodes = Object.fromEntries(['button', 'consent', 'status', 'result', 'editor', 'panel', 'window'].map(key => [key, new Element()]));
  nodes.editor.value = 'Mam problem';
  nodes.panel.dataset = {aiEditor: 'editor', aiUrl: '/review/', aiToken: 'fixture', ...(speech ? {aiSpeech: '1'} : {})};
  nodes.panel.querySelector = selector => ({'[data-ai-submit]': nodes.button, '[data-ai-consent]': nodes.consent, '[data-ai-confirmed]': nodes.consent, '[data-ai-status]': nodes.status, '[data-ai-result]': nodes.result})[selector];
  nodes.panel.closest = () => ({querySelectorAll: () => []});
  const requests = [], timers = new Map(); let timerId = 0;
  vm.runInNewContext(source, {
    document: {documentElement: {lang: language}, querySelectorAll: () => [nodes.panel], querySelector: () => ({value: 'csrf'}), getElementById: () => nodes.editor, createElement: () => new Element()},
    window: nodes.window, AbortController,
    setTimeout(fn) {const id = ++timerId; timers.set(id, fn); return id;}, clearTimeout(id) {timers.delete(id);},
    fetch(url, options) {return new Promise((resolve, reject) => requests.push({url, options, fail: reject, deliver(payload, ok = true) {resolve({ok, json: async () => payload});}}));},
  });
  return {nodes, requests, timers};
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
    n.consent.checked = true; n.button.dispatchEvent(new Event('click'));
    requests[4].deliver({result}); await flush(); assert.equal(n.result.hidden, false);
    n.editor.dispatchEvent(new Event('lingoflow:writing-reset'));
    assert.equal(n.consent.checked, false); assert.equal(n.result.children.length, 0); assert.equal(n.result.hidden, true);
    n.consent.checked = true; n.button.dispatchEvent(new Event('click'));
    n.editor.dispatchEvent(new Event('lingoflow:writing-reset'));
    assert.equal(requests[5].options.signal.aborted, true);
    n.consent.checked = true; // A fresh permission must not revive a previous request with identical text.
    requests[5].deliver({result}); await flush(); assert.equal(n.result.hidden, true);
  }
  for (const speech of [false, true]) {
    const {nodes: n, requests, timers} = setup('en', speech);
    n.consent.checked = true;
    n.button.dispatchEvent(new Event('click')); requests[0].deliver({result}); await flush();
    const previous = n.result.children;
    n.button.dispatchEvent(new Event('click')); n.button.dispatchEvent(new Event('click'));
    assert.equal(requests.length, 2, 'double click cannot submit twice');
    requests[1].deliver({error: 'Quota reached'}, false); await flush();
    assert.equal(n.result.hidden, false, 'a failed retry preserves the previous report');
    assert.equal(n.result.children, previous);
    assert.equal(n.editor.value, 'Mam problem');
    n.button.dispatchEvent(new Event('click')); requests[2].fail(new TypeError('Load failed')); await flush();
    assert.equal(n.result.hidden, false);
    assert(!n.status.textContent.includes('Load failed'), 'browser-specific errors are localized');
    n.button.dispatchEvent(new Event('click')); requests[3].deliver({result: {score: 10}}); await flush();
    assert.equal(n.result.children, previous, 'an incomplete success cannot erase a good report');
    assert.equal(n.result.hidden, false);
    n.button.dispatchEvent(new Event('click')); [...timers.values()][0]();
    assert.equal(requests[4].options.signal.aborted, true);
    requests[4].fail(Object.assign(new Error(), {name: 'AbortError'})); await flush();
    assert.equal(n.result.hidden, false, 'timeout preserves the previous report');
    n.button.dispatchEvent(new Event('click'));
    n.editor.value = 'New draft'; n.editor.dispatchEvent(new Event('input'));
    requests[5].deliver({error: 'Old error'}, false); await flush();
    assert.equal(n.result.hidden, true); assert.equal(n.status.textContent, '');
    n.button.dispatchEvent(new Event('click')); requests[6].deliver({result}); await flush();
    assert.equal(n.result.hidden, false); assert.equal(n.button.disabled, false);
    assert.equal(timers.size, 0);
  }
  console.log('AI writing/transcript: consent revocation, stale response, pagehide, language and escaped correction PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
