const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, 'learning/static/polskiflow/audio-session.js'), 'utf8');
for (const mode of ['supported', 'missing', 'throws']) {
  const navigator = {};
  if (mode === 'supported') navigator.audioSession = {type: 'auto'};
  if (mode === 'throws') navigator.audioSession = {set type(_) {throw new Error('unsupported');}};
  let play;
  const context = {navigator, window: {}, document: {addEventListener(name, callback, capture) {
    assert.equal(name, 'play'); assert.equal(capture, true); play = callback;
  }}};
  vm.runInNewContext(source, context);
  const session = context.window.PolskiFlowAudioSession;
  const release = session.beginCapture();
  const secondRelease = session.beginCapture();
  release(); release();
  play({target: {tagName: 'AUDIO'}});
  if (mode === 'supported') assert.equal(navigator.audioSession.type, 'play-and-record', 'another capture is still active');
  secondRelease();
  if (mode === 'supported') assert.equal(navigator.audioSession.type, 'playback');
  let loaded = false;
  const audio = {muted: true, volume: 0, setAttribute(name) {assert.equal(name, 'playsinline');}, load() {loaded = true;}};
  session.prepare(audio);
  assert.equal(audio.muted, false); assert.equal(audio.volume, 1); assert.equal(loaded, true);
  if (mode === 'supported') {
    navigator.audioSession.type = 'auto';
    play({target: {tagName: 'AUDIO'}});
    assert.equal(navigator.audioSession.type, 'playback', 'saved clip playback also restores the speaker session');
  }
}
console.log('Audio session compatibility: PASS');
