const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'learning/static/polskiflow/audio-session.js'),'utf8');
function fixture(userAgent='iPhone', mode='resolve') {
 const created=[],events={},documentEvents={};
 const navigator={userAgent,maxTouchPoints:userAgent==='Macintosh'?5:0,audioSession:{type:'auto'}};
 const document={currentScript:{dataset:{speechMediaSrc:'/speech-session.wav'}},body:{append(){}},hidden:false,
 addEventListener(name,fn){documentEvents[name]=fn;},createElement(tag){
 assert.equal(tag,'audio');const media={attributes:{},paused:false,removed:false,
 setAttribute(k,v){this.attributes[k]=v;},removeAttribute(k){delete this[k];},load(){},remove(){this.removed=true;},pause(){this.paused=true;},
 play(){this.played=true;if(mode==='throws')throw Error('blocked');return mode==='reject'?Promise.reject(Error('blocked')):Promise.resolve();}};
 created.push(media);return media;
 }};
 const window={addEventListener(name,fn){events[name]=fn;}};
 vm.runInNewContext(source,{window,document,navigator});
 return {session:window.PolskiFlowAudioSession,created,events,documentEvents,document,navigator};
}
const utterance=()=>new EventTarget();
(async()=>{
 for(const ua of ['iPhone','iPad','Macintosh']){
 const f=fixture(ua);assert.equal(f.created.length,0,'no autoplay on load');
 const first=utterance();f.session.prepareSpeech(first);assert.equal(f.created.length,1);
 const media=f.created[0];assert.equal(media.played,true,'play is synchronous with prepare');assert.equal(media.loop,true);assert.equal(media.muted,false);assert.equal(media.volume,1);
 const second=utterance();f.session.prepareSpeech(second);assert.ok(media.paused&&media.removed);
 first.dispatchEvent(new Event('end'));assert.equal(f.created[1].paused,false,'stale end cannot stop replacement');
 second.dispatchEvent(new Event('end'));assert.equal(f.created[1].paused,true);
 f.session.prepareSpeech(utterance());f.events.pagehide();assert.equal(f.created[2].paused,true);
 f.session.prepareSpeech(utterance());f.document.hidden=true;f.documentEvents.visibilitychange();assert.equal(f.created[3].paused,true);
 const release=f.session.beginCapture();f.session.prepareSpeech(utterance());assert.equal(f.created.length,4,'no playback bridge during capture');assert.equal(f.navigator.audioSession.type,'play-and-record');release();
 }
 const desktop=fixture('Chrome Windows');desktop.session.prepareSpeech(utterance());assert.equal(desktop.created.length,0);
 for(const mode of ['reject','throws']){const f=fixture('iPhone',mode);f.session.prepareSpeech(utterance());await new Promise(resolve=>setImmediate(resolve));assert.ok(f.created[0].paused&&f.created[0].removed);}
 const unsupported=fixture();delete unsupported.navigator.audioSession;unsupported.session.prepareSpeech(utterance());assert.equal(unsupported.created[0].played,true);
 const wav=fs.readFileSync(path.join(__dirname,'learning/static/polskiflow/audio/speech-session.wav'));
 assert.equal(wav.toString('ascii',0,4),'RIFF');assert.equal(wav.toString('ascii',8,12),'WAVE');assert.equal(wav.readUInt16LE(34),16);assert.equal(wav.readUInt32LE(24),44100);assert.ok(wav.subarray(44).every(byte=>byte===0),'PCM must be exact digital silence');
 console.log('iOS speech media bridge: gesture, lifecycle, stale events, capture, failures and silent WAV PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
