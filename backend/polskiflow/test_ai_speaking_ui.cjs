const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
class Element extends EventTarget { constructor(){super();this.value='';this.dataset={};this.checked=false;this.hidden=false;} focus(){} }
const nodes=Object.fromEntries(['button','consent','confirmed','status','editor','text','panel','recorder','window'].map(k=>[k,new Element()]));
nodes.panel.dataset={aiRecordingToken:'owner-recording-token',transcribeUrl:'/speaking/ai-transcribe/'};
nodes.panel.closest=()=>nodes.recorder;
nodes.panel.querySelector=s=>({'[data-ai-transcribe]':nodes.button,'[data-ai-audio-consent]':nodes.consent,'[data-ai-confirmed]':nodes.confirmed,'[data-transcribe-status]':nodes.status,'[data-speech-text]':nodes.text}[s]);
const calls=[];let deliver;
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'learning/static/polskiflow/ai-speaking.js'),'utf8'),{
 document:{querySelector:s=>s==='[data-ai-speaking]'?nodes.panel:{value:'csrf'},getElementById:()=>nodes.editor},window:nodes.window,
 Event,FormData,AbortController,setTimeout,clearTimeout,
 fetch:(url,options)=>{calls.push({url,options});return new Promise(resolve=>{deliver=value=>resolve({ok:true,json:async()=>value});});}
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
 console.log('PASS: explicit audio consent, confirmation invalidation, deletion and revoked-consent stale responses');
})().catch(error=>{console.error(error);process.exitCode=1;});
