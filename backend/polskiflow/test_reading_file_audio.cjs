const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = Object.fromEntries(['play','pause','stop','rate','status'].map(k => [k,{events:{},value:'1',addEventListener(e,f){this.events[e]=f;}}]));
let prepared=0, reject, timer;
const audio={events:{},currentTime:0,paused:true,ended:false,addEventListener(e,f){this.events[e]=f;},play(){this.paused=false;this.events.playing();return new Promise((_,r)=>{reject=r;});},pause(){this.paused=true;this.events.pause();}};
const events={};
const panel={querySelector(s){return s==='.reading-audio-actions'||s==='.reading-audio-rate'?{}:s==='[data-reading-player]'?audio:elements[s.match(/data-audio-(\w+)/)[1]];}};
vm.runInNewContext(fs.readFileSync(__dirname+'/learning/static/polskiflow/reading-audio.js','utf8'),{setTimeout(fn){timer=fn;return 1;},clearTimeout(){timer=null;},document:{querySelector(){return panel;}},window:{PolskiFlowAudioSession:{prepare(){prepared++;}},addEventListener(e,f){events[e]=f;}}});
(async()=>{
 elements.play.events.click();assert.equal(prepared,1);assert.equal(elements.pause.disabled,false);
 const stale=reject;audio.currentTime=12;elements.pause.events.click();elements.play.events.click();assert.equal(audio.currentTime,12);assert.equal(prepared,1,'resume preserves position');
 elements.rate.value='0.8';elements.rate.events.change();assert.equal(audio.playbackRate,0.8);
 elements.stop.events.click();stale(new Error('late'));audio.events.pause();audio.events.error();await Promise.resolve();assert.equal(audio.currentTime,0);assert.equal(elements.status.textContent,'Воспроизведение остановлено');
 elements.play.events.click();audio.currentTime=20;audio.error={code:2};audio.events.error();elements.play.events.click();assert.equal(audio.currentTime,0,'failed media reloads before retry');audio.error=null;audio.currentTime=20;events.pagehide();assert.equal(audio.paused,true);assert.equal(audio.currentTime,0);
 audio.play=()=>new Promise((_,r)=>{reject=r;});elements.play.events.click();const timeout=timer;timeout();audio.events.playing();audio.events.ended();assert.ok(audio.paused);assert.equal(elements.status.textContent,'Не удалось воспроизвести аудио. Попробуй ещё раз.');
 console.log('Reading AAC pause/resume, speed, stale rejection, stop, pagehide and stalled loading: PASS');
})();
