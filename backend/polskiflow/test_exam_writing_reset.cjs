const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
class El extends EventTarget {constructor(){super();this.value='';this.hidden=false;this.checked=false;this.dataset={};this.textContent='';}focus(){} }
const source=fs.readFileSync(path.join(__dirname,'learning/static/polskiflow/b1-exam-writing.js'),'utf8');
const editors=[new El(),new El()],checks=[new El(),new El()],reviews=[new El(),new El()];let resets=0;
for(const e of editors){e.addEventListener('lingoflow:writing-reset',()=>resets++);e.closest=()=>({dataset:{target:50},querySelector:()=>new El()});}
const names=['status','clock','start','finish','dialog','storage','result','cancel','confirm','again'];
const nodes=Object.fromEntries(names.map(n=>[n,new El()]));nodes.status.textContent='idle';nodes.dialog.close=()=>nodes.dialog.open=false;nodes.dialog.showModal=()=>nodes.dialog.open=true;
const root={dataset:{set:'1',owner:'fixture'},querySelector:s=>nodes[s.match(/data-exam-(\w+)/)[1]],querySelectorAll:s=>s==='[data-exam-draft]'?editors:s==='[data-exam-review]'?reviews:s==='[data-exam-result] input[type="checkbox"]'?checks:[]};
const key='lingoflow-exam-writing-v1:fixture',store=new Map(),win=new EventTarget();
const item={status:'finished',deadline:Date.now()+60000,texts:['Old essay','Old letter'],remaining:42};store.set(key,JSON.stringify({'1':item}));
vm.runInNewContext(source,{document:{querySelector:()=>root,querySelectorAll:()=>[],addEventListener(){}},window:win,localStorage:{getItem:k=>store.get(k)||null,setItem:(k,v)=>store.set(k,v)},location:{replace(){throw Error('Unexpected redirect');}},Event,Date,setInterval(){}});
assert.equal(editors[0].value,'Old essay');checks.forEach(c=>c.checked=true);let before=resets;
nodes.again.dispatchEvent(new Event('click'));assert.equal(editors[0].value,'Old essay','restart intent keeps draft until Start');
nodes.start.dispatchEvent(new Event('click'));assert.deepEqual(editors.map(e=>e.value),['','']);assert.equal(resets,before+2);assert(checks.every(c=>!c.checked));
function storage(k){const e=new Event('storage');Object.defineProperty(e,'key',{value:k});win.dispatchEvent(e);}
before=resets;const current=JSON.parse(store.get(key));store.set(key,JSON.stringify({...current,'2':item}));storage(key);assert.equal(resets,before,'unrelated completed set preserves current review');
store.set(key,JSON.stringify({'1':{...item,texts:['Same text','Same text']}}));storage(key);assert.equal(resets,before+2);assert.equal(editors[0].value,'Same text');
checks.forEach(c=>c.checked=true);before=resets;store.set(key,JSON.stringify({'1':{...item,deadline:item.deadline+1,texts:['Same text','Same text']}}));storage(key);assert.equal(resets,before+2,'identical text in a different attempt still invalidates');assert(checks.every(c=>!c.checked));
store.delete(key);storage(null);assert.deepEqual(editors.map(e=>e.value),['','']);assert(editors.every(e=>e.disabled));assert.equal(nodes.status.textContent,'idle');assert.equal(nodes.clock.textContent,'75:00');console.log('Exam writing: new attempt, cross-tab draft, identical-text replacement and storage clear reset PASS');
