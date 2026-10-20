const {test} = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const {harness, button, nodes, text, deferred, flush} = require('./component-harness.cjs');
function fixture(name, apiName, api, extra = {}) {
  const mocks = {[apiName]: api, ...extra};
  mocks['../lib/request-gate'] = harness(path.join(__dirname, '../src/lib/request-gate.ts')).exports;
  const h = harness(path.join(__dirname, '../src/components/'+name+'Screen.tsx'), mocks);
  h.render({session: {access_token: 'fixture-token'}, colors: {}, onClose() {}}, h.exports[name+'Screen']); return h;
}
const prompt = id => ({id, title: id, level: 'B1', task: 'Task', hint: 'Hint', minimum_words: 2, minimum_paragraphs: 1, required_markers: [], checklist: []});
function writer() {const calls = [], h = fixture('Writing', '../lib/writing-api', {loadWritingPrompts: async () => ({prompts: [prompt('A'), prompt('B')]}), checkWritingDraft(...args) {const wait = deferred(); calls.push({args, ...wait}); return wait.promise;}});return {h, calls};}
function input(h, value) {nodes(h.tree).find(n => n.type === 'TextInput').props.onChangeText(value); h.render();}
const writingResult = id => ({prompt_id: id, checks: [], limitations: 'Old review', all_observable_checks_passed: true});
test('writing: an edited draft cannot receive the old result', async () => {
  const {h, calls} = writer(); await flush(); h.render(); input(h, 'Old draft'); button(h.tree, 'Проверить структуру').onPress();
  input(h, 'New draft'); calls[0].resolve(writingResult('A')); await flush(); h.render();
  assert(!nodes(h.tree).some(n => n.type === 'Text' && text(n).includes('Old review'))); assert.equal(nodes(h.tree).find(n => n.type === 'TextInput').props.value, 'New draft');
});
test('writing: prompt change ignores old errors and does not unlock a newer check', async () => {
  const {h, calls} = writer(); await flush(); h.render(); input(h, 'Text A'); button(h.tree, 'Проверить структуру').onPress();
  button(h.tree, 'B1 · B').onPress(); h.render(); input(h, 'Text B'); button(h.tree, 'Проверить структуру').onPress(); h.render();
  calls[0].reject(Error('stale failure')); await flush(); h.render(); assert(button(h.tree, 'Проверяем…').disabled);
  calls[1].resolve(writingResult('B')); await flush(); h.render(); assert(nodes(h.tree).some(n => n.type === 'Text' && text(n).includes('Old review')));
});
test('writing: rapid taps produce one request and failure permits retry', async () => {
  const {h, calls} = writer(); await flush(); h.render(); input(h, 'Text A'); const press = button(h.tree, 'Проверить структуру').onPress;
  press(); press(); assert.equal(calls.length, 1); calls[0].reject(Error('offline')); await flush(); h.render();
  button(h.tree, 'Проверить структуру').onPress(); assert.equal(calls.length, 2); calls[1].resolve(writingResult('A')); await flush();
});
const scenario = id => ({id, title: id, level: 'B1', mode: 'dialogue', situation: 'Situation', kind: 'choice', prompt: 'Choose', options: [{id:'one',text:'One'},{id:'two',text:'Two'}]});
function interaction() {const calls = [], h = fixture('Interaction', '../lib/interaction-api', {loadInteraction: async () => [scenario('A'),scenario('B')], checkInteraction(...args) {const wait = deferred(); calls.push({args,...wait}); return wait.promise;}});return {h,calls};}
test('interaction: changing answer or scenario discards stale feedback', async () => {
  const {h,calls} = interaction(); await flush();h.render();button(h.tree,'One').onPress();h.render();button(h.tree,'Проверить ответ').onPress();
  button(h.tree,'Two').onPress();h.render();calls[0].resolve({correct:true,explanation:'Old answer'});await flush();h.render();assert(!text(h.tree).includes('Old answer'));
  button(h.tree,'Проверить ответ').onPress();button(h.tree,'B1 · B').onPress();h.render();calls[1].resolve({correct:true,explanation:'Old scenario'});await flush();h.render();assert(!text(h.tree).includes('Old scenario'));
});
test('interaction: synchronous submission lock and recovery after failure', async () => {
  const {h,calls}=interaction();await flush();h.render();button(h.tree,'One').onPress();h.render();const press=button(h.tree,'Проверить ответ').onPress;press();press();assert.equal(calls.length,1);
  calls[0].reject(Error('offline'));await flush();h.render();assert.equal(button(h.tree,'Проверить ответ').disabled,false);button(h.tree,'Проверить ответ').onPress();calls[1].resolve({correct:true,explanation:'Current'});await flush();h.render();assert(text(h.tree).includes('Current'));
});
function listener() {const calls=[], row=id=>({id,title:id,level:'B1',delivery:'device_tts',transcript:'Text',fragments:[],questions:[{id:'shared',prompt:'Question',options:['Tak','Nie']}]}),h=fixture('Listening','../lib/api',{loadListening:async()=>[row('A'),row('B')],checkListeningAnswer(...args){const wait=deferred();calls.push({args,...wait});return wait.promise;}},{'expo-speech':{stop:async()=>{},speak(){}}});return{h,calls};}
function chooseListening(h,id) {const n=nodes(h.tree).find(n=>n.type==='Pressable'&&text(n).startsWith(id+'B1')); if(!n)throw Error('missing listening '+id);n.props.onPress();h.render();}
test('listening: response from a previous exercise cannot mark a shared question ID', async()=>{
  const {h,calls}=listener();await flush();h.render();chooseListening(h,'A');button(h.tree,'Tak').onPress();button(h.tree,'‹ Все упражнения').onPress();h.render();chooseListening(h,'B');
  calls[0].resolve({question_id:'shared',correct:true,correct_index:0,explanation:'Old listening'});await flush();h.render();assert(!text(h.tree).includes('Old listening'));assert.equal(button(h.tree,'Tak').disabled,false);
});
test('listening: rapid taps submit once and failed checks can be retried', async()=>{
  const {h,calls}=listener();await flush();h.render();chooseListening(h,'A');const press=button(h.tree,'Tak').onPress;press();press();assert.equal(calls.length,1);calls[0].reject(Error('offline'));await flush();h.render();button(h.tree,'Tak').onPress();calls[1].resolve({question_id:'shared',correct:true,correct_index:0,explanation:'Current listening'});await flush();h.render();assert(text(h.tree).includes('Current listening'));
});

test('interaction: rapid sequence taps cannot duplicate or lose blocks', async()=>{
  const calls=[],row={...scenario('S'),kind:'sequence',blocks:[{id:'a',text:'First block'},{id:'b',text:'Second block'}]},h=fixture('Interaction','../lib/interaction-api',{loadInteraction:async()=>[row],checkInteraction(...args){calls.push(args);return Promise.resolve({scenario_id:'S',correct:true,explanation:'Sequence OK'})}});
  await flush();h.render();const first=button(h.tree,'First block').onPress;first();first();button(h.tree,'Second block').onPress();h.render();button(h.tree,'Проверить ответ').onPress();
  assert.deepEqual(Array.from(calls[0][1].block_ids),['a','b']);await flush();
});
test('listening: a late old response cannot re-enable options during a newer check', async()=>{
  const {h,calls}=listener();await flush();h.render();chooseListening(h,'A');button(h.tree,'Tak').onPress();button(h.tree,'‹ Все упражнения').onPress();h.render();chooseListening(h,'B');button(h.tree,'Nie').onPress();h.render();
  calls[0].resolve({question_id:'shared',correct:true,correct_index:0,explanation:'Old'});await flush();h.render();assert.equal(button(h.tree,'Tak').disabled,true);assert(!text(h.tree).includes('Old'));
  calls[1].resolve({question_id:'shared',correct:false,correct_index:0,explanation:'Current B'});await flush();h.render();assert(text(h.tree).includes('Current B'));
});
test('writing: switching away and back still invalidates the old check', async()=>{
  const {h,calls}=writer();await flush();h.render();input(h,'Text A');button(h.tree,'Проверить структуру').onPress();button(h.tree,'B1 · B').onPress();h.render();button(h.tree,'B1 · A').onPress();h.render();
  calls[0].resolve(writingResult('A'));await flush();h.render();assert(!nodes(h.tree).some(n=>n.type==='Text'&&text(n).includes('Old review')));assert.equal(nodes(h.tree).find(n=>n.type==='TextInput').props.value,'Text A');
});
