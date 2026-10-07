(() => {
  let captures = 0;
  const setType = type => {
    // Older browsers do not expose AudioSession; recording must still work.
    try { if (navigator.audioSession) navigator.audioSession.type = type; } catch (_) {}
  };
  const playback = () => { if (!captures) setType('playback'); };
  window.PolskiFlowAudioSession = {
    beginCapture() {
      captures++;
      setType('play-and-record');
      let released = false;
      return () => {
        if (released) return;
        released = true;
        captures--;
        playback();
      };
    },
    prepare(audio) {
      playback();
      audio.muted = false;
      audio.volume = 1;
      audio.setAttribute('playsinline', '');
      audio.load();
    },
  };
  // Includes saved answers and native controls, without autoplaying a clip.
  document.addEventListener('play', event => {
    if (event.target.tagName === 'AUDIO') playback();
  }, true);
})();
