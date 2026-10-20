const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
class Element extends EventTarget { constructor(){super();this.value='';this.dataset={};this.checked=false;this.hidden=false;} focus(){} }
const nodes=Object.fromEntries(['button','consent','confirmed','status','editor','text','panel','recorder','window'].map(k=>[k,new Element()]));
nodes.panel.dataset={aiRecordingToken:'owner-recording-token',transcribeUrl:'/speaking/ai-transcribe/'};
nodes.panel.closest=()=>nodes.recorder;
nodes.panel.querySelector=s=>({'[data-ai-transcribe]':nodes.button,'[data-ai-audio-consent]':nodes.consent,'[data-ai-confirmed]':nodes.confirmed,'[data-transcribe-status]':nodes.status,'[data-speech-text]':nodes.text}[s]);
const calls=[],timers=new Map();let timerId=0,deliver,fail;
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'learning/static/polskiflow/ai-speaking.js'),'utf8'),{
 document:{querySelector:s=>s==='[data-ai-speaking]'?nodes.panel:{value:'csrf'},getElementById:()=>nodes.editor},window:nodes.window,
 Event,FormData,AbortController,
 setTimeout(fn){const id=++timerId;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);},
 fetch:(url,options)=>{calls.push({url,options});return new Promise((resolve,reject)=>{fail=reject;deliver=(value,ok=true)=>resolve({ok,json:async()=>value});});}
});
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const ready=()=>nodes.recorder.dispatchEvent(new CustomEvent('b1-recording-ready',{detail:{blob:new Blob(['audio'],{type:'audio/webm'})}}));
(async()=>{
 ready();nodes.button.dispatchEvent(new Event('click'));assert.equal(calls.length,0,'no request without audio consent');
 nodes.consent.checked=true;nodes.button.dispatchEvent(new Event('click'));assert.equal(calls.length,1);
 assert.equal(calls[0].options.body.get('consent'),'true');assert.equal(calls[0].options.body.get('token'),'owner-recording-token');
 deliver({text:'Mam problem',token:'transcript-receipt'});await flush();assert.equal(nodes.editor.value,'Mam problem');assert.equal(nodes.confirmed.checked,false);assert.equal(nodes.text.hidden,false);
 nodes.confirmed.checked=true;nodes.editor.value='Mam pytanie';nodes.editor.dispatchEvent(new Event('input'));assert.equal(nodes.confirmed.checked,false,'editing invalidates confirmation');
 nodes.button.dispatchEvent(new Event('click'));assert.equal(calls.length,2);const late=deliver;
 nodes.recorder.dispatchEvent(new Event('b1-recording-cleared'));assert.equal(nodes.panel.dataset.aiToken,'');assert.equal(nodes.editor.value,'');assert.equal(nodes.text.hidden,true);assert.equal(nodes.button.disabled,true);
 late({text:'stale text',token:'stale-token'});await flush();assert.equal(nodes.editor.value,'','late response must not resurrect deleted audio or transcript');assert.equal(nodes.panel.dataset.aiToken,'');
 ready();nodes.consent.checked=true;nodes.button.dispatchEvent(new Event('click'));assert.equal(calls.length,3);
 nodes.consent.checked=false;nodes.consent.dispatchEvent(new Event('change'));deliver({text:'revoked',token:'revoked'});await flush();assert.equal(nodes.editor.value,'');
 ready();nodes.consent.checked=true;nodes.button.dispatchEvent(new Event('click'));
 deliver({text:'Original transcript',token:'receipt'});await flush();
 nodes.editor.value='My corrected transcript';nodes.editor.dispatchEvent(new Event('input'));nodes.confirmed.checked=true;
 for(const mode of ['quota','network','malformed','timeout']){
   nodes.button.dispatchEvent(new Event('click'));
   if(mode==='quota')deliver({error:'Quota reached'},false);
   if(mode==='network')fail(new TypeError('Load failed'));
   if(mode==='malformed')deliver({text:null,token:'broken'});
   if(mode==='timeout'){[...timers.values()][0]();assert.equal(calls.at(-1).options.signal.aborted,true);fail(Object.assign(new Error(),{name:'AbortError'}));}
   await flush();
   assert.equal(nodes.editor.value,'My corrected transcript','failed retranscription preserves edits');
   assert.equal(nodes.panel.dataset.aiToken,'receipt');assert.equal(nodes.text.hidden,false);assert.equal(nodes.confirmed.checked,true);
   assert.equal(nodes.button.disabled,false);
 }
 nodes.button.dispatchEvent(new Event('click'));const stale=deliver,oldCall=calls.at(-1);
 nodes.editor.value='Continue editing';nodes.editor.dispatchEvent(new Event('input'));
 assert.equal(oldCall.options.signal.aborted,true,'editing cancels the pending replacement');
 stale({text:'Replacement must not erase edits',token:'stale'});await flush();
 assert.equal(nodes.editor.value,'Continue editing');assert.equal(nodes.panel.dataset.aiToken,'receipt');assert.equal(nodes.confirmed.checked,false);
 nodes.button.dispatchEvent(new Event('click'));const number=calls.length;nodes.button.dispatchEvent(new Event('click'));assert.equal(calls.length,number);
 deliver({text:'New transcript',token:'new-receipt'});await flush();
 assert.equal(nodes.editor.value,'New transcript');assert.equal(nodes.panel.dataset.aiToken,'new-receipt');assert.equal(nodes.confirmed.checked,false);
 nodes.window.dispatchEvent(new Event('pagehide'));assert.equal(nodes.editor.value,'');assert.equal(nodes.panel.dataset.aiToken,'');
 console.log('PASS: audio consent, retries with quota/network/timeout/malformed responses, preserved edits, cancellation and stale responses');
})().catch(error=>{console.error(error);process.exitCode=1;});
