const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'learning/static/polskiflow/listening-player.js'),'utf8');
function fixture(mode='normal'){
const players={},created=[],events={},timers=new Map();let id=0;
const control=()=>({value:'1',disabled:true,textContent:'',events:{},addEventListener(k,fn){this.events[k]=fn;}});
for(const name of ['dialogue','b1','b2']){const controls=Object.fromEntries(['play','repeat','rate','status','stop'].map(k=>[k,control()]));const fragment={...control(),dataset:{dialogueFragment:'0'}};
players[name]={dataset:{mediaId:name},controls,fragment,append(){},querySelector(s){return controls[s.match(/-(play|repeat|rate|status|stop)/)[1]];},querySelectorAll(s){return s==='[data-dialogue-fragment]'?(name==='dialogue'?[fragment]:[]):Object.values(controls);}};}
vm.runInNewContext(source,{document:{querySelector(s){return players[s.match(/data-(dialogue|b1|b2)-player/)[1]];},getElementById(id){return {textContent:JSON.stringify(mode==='missing'?{}:{full:'/'+id+'.m4a','fragment-0':'/fragment.m4a'})};},createElement(){const audio={setAttribute(){},pause(){this.paused=true;},removeAttribute(k){delete this[k];},load(){},remove(){this.removed=true;},play(){this.played=true;if(mode==='throws')throw Error('denied');return mode==='reject'?Promise.reject(Error('denied')):Promise.resolve();}};created.push(audio);return audio;}},window:{addEventListener(k,fn){events[k]=fn;},PolskiFlowAudioSession:{prepare(a){a.prepared=true;}}},setTimeout(fn){const key=++id;timers.set(key,fn);return key;},clearTimeout(key){timers.delete(key);}});
return {players,created,events,timers};}
(async()=>{
const f=fixture();
for(const player of Object.values(f.players)){player.controls.play.events.click();const a=f.created.at(-1);assert.ok(a.played&&a.prepared);assert.equal(player.controls.status.textContent,'Аудио загружается…');a.onplaying();assert.equal(f.timers.size,0);a.onended();assert.ok(a.removed&&a.paused);assert.equal(player.controls.stop.disabled,true);}
const d=f.players.dialogue.controls,b=f.players.b1.controls;
d.play.events.click();const old=f.created.at(-1),latePlay=old.onplaying,lateEnd=old.onended,lateError=old.onerror;b.play.events.click();latePlay();lateEnd();lateError();assert.equal(b.status.textContent,'Аудио загружается…');
b.stop.events.click();assert.ok(f.created.at(-1).removed);
d.repeat.events.click();[...f.timers.values()][0]();assert.equal(d.status.textContent,'Не удалось воспроизвести аудио. Попробуй ещё раз.');
f.players.dialogue.fragment.events.click();assert.equal(f.created.at(-1).src,'/fragment.m4a');d.repeat.events.click();assert.equal(f.created.at(-1).src,'/fragment.m4a');f.events.pagehide();assert.equal(f.timers.size,0);assert.ok(f.created.at(-1).removed);
const missing=fixture('missing');assert.equal(missing.created.length,0);assert.equal(missing.players.b1.controls.play.disabled,true);
for(const mode of ['throws','reject']){const t=fixture(mode);t.players.b2.controls.play.events.click();await new Promise(r=>setImmediate(r));assert.equal(t.players.b2.controls.status.textContent,'Не удалось воспроизвести аудио. Попробуй ещё раз.');assert.ok(t.created[0].removed);}
console.log('Practice media: playing/end/stop/timeout, stale events, fragments, rejected play and pagehide PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
