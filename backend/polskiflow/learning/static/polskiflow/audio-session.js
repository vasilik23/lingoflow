(() => {
  let captures = 0;
  let currentSpeech = null;
  let speechMedia = null;
  const speechMediaSrc = document.currentScript?.dataset.speechMediaSrc;
  const ios = /iPad|iPhone|iPod/.test(navigator.userAgent || '') ||
    (/Macintosh/.test(navigator.userAgent || '') && navigator.maxTouchPoints > 1);
  const stopSpeech = utterance => {
    if (utterance && utterance !== currentSpeech) return;
    currentSpeech = null;
    if (!speechMedia) return;
    const media = speechMedia;
    speechMedia = null;
    media.pause();
    media.removeAttribute('src');
    media.load();
    media.remove();
  };
  const setType = type => {
    // Older browsers do not expose AudioSession; recording must still work.
    try { if (navigator.audioSession) navigator.audioSession.type = type; } catch (_) {}
  };
  const playback = () => { if (!captures) setType('playback'); };
  window.PolskiFlowAudioSession = {
    prepareSpeech(utterance) {
      stopSpeech();
      // Keep the active utterance alive while Safari owns its callbacks.
      currentSpeech = utterance || null;
      playback();
      if (!ios || captures || !speechMediaSrc || !utterance) return;
      // iOS speech can stay on the ringer channel despite AudioSession.
      // A silent media element keeps the playback channel active. Start it
      // synchronously with the tap; never autoplay or run it in the background.
      const media = document.createElement('audio');
      speechMedia = media;
      media.src = speechMediaSrc;
      media.loop = true;
      media.muted = false;
      media.volume = 1;
      media.hidden = true;
      media.setAttribute('playsinline', '');
      media.setAttribute('aria-hidden', 'true');
      document.body.append(media);
      const finish = () => stopSpeech(utterance);
      utterance.addEventListener?.('end', finish, {once: true});
      utterance.addEventListener?.('error', finish, {once: true});
      try {
        media.play()?.then(() => {
          if (currentSpeech === utterance) playback();
        }).catch(() => { if (speechMedia === media) stopSpeech(utterance); });
      } catch (_) { stopSpeech(utterance); }
    },
    stopSpeech,
    beginCapture() {
      stopSpeech();
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
  window.addEventListener?.('pagehide', () => stopSpeech());
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopSpeech();
  });
  document.addEventListener('play', event => {
    if (event.target.tagName === 'AUDIO') playback();
  }, true);
})();
