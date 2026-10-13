(() => {
  const panel = document.querySelector('[data-reading-audio]');
  const audio = panel?.querySelector('[data-reading-player]');
  if (!audio) return;
  audio.controls = false;
  panel.querySelector('.reading-audio-actions').hidden = false;
  panel.querySelector('.reading-audio-rate').hidden = false;
  const ui = window.PolskiFlowI18n?.t || ((text) => text);
  const play = panel.querySelector('[data-audio-play]');
  const pause = panel.querySelector('[data-audio-pause]');
  const stop = panel.querySelector('[data-audio-stop]');
  const rate = panel.querySelector('[data-audio-rate]');
  const status = panel.querySelector('[data-audio-status]');
  let attempt = 0;
  let stopped = true;
  let failed = false;
  let watchdog = null;
  const clearWatchdog = () => { clearTimeout(watchdog); watchdog = null; };
  const update = () => {
    pause.disabled = audio.paused;
    stop.disabled = audio.paused && audio.currentTime === 0;
  };
  play.addEventListener('click', () => {
    const current = ++attempt;
    clearWatchdog();
    const restart = failed || audio.error || !audio.paused || audio.ended;
    stopped = false;
    failed = false;
    if (restart) audio.currentTime = 0;
    if (audio.currentTime === 0) {
      if (window.PolskiFlowAudioSession?.prepare) window.PolskiFlowAudioSession.prepare(audio);
      else audio.load();
    }
    audio.playbackRate = Number(rate.value);
    status.textContent = ui('Подготавливаем аудиозапись…');
    stop.disabled = false;
    watchdog = setTimeout(() => {
      if (current !== attempt) return;
      ++attempt; failed = true; audio.pause(); update();
      status.textContent = ui('Не удалось воспроизвести аудио. Попробуй ещё раз.');
    }, 10000);
    audio.play().catch(() => {
      if (current === attempt) { clearWatchdog(); failed = true; status.textContent = ui('Не удалось воспроизвести аудио. Попробуй ещё раз.'); update(); }
    });
  });
  pause.addEventListener('click', () => { ++attempt; clearWatchdog(); audio.pause(); });
  const reset = () => { ++attempt; stopped = true; clearWatchdog(); audio.pause(); audio.currentTime = 0; update(); status.textContent = ui('Воспроизведение остановлено'); };
  stop.addEventListener('click', reset);
  rate.addEventListener('change', () => { audio.playbackRate = Number(rate.value); });
  audio.addEventListener('playing', () => { clearWatchdog(); if (!stopped && !failed && !audio.paused) status.textContent = ui('Воспроизведение'); update(); });
  audio.addEventListener('pause', () => { if (!stopped && !failed && !audio.error && !audio.ended) status.textContent = ui('Пауза'); update(); });
  audio.addEventListener('ended', () => { if (!stopped && !failed) status.textContent = ui('Текст прослушан'); update(); });
  audio.addEventListener('error', () => { clearWatchdog(); if (!stopped) { ++attempt; failed = true; status.textContent = ui('Не удалось воспроизвести аудио. Попробуй ещё раз.'); } update(); });
  window.addEventListener('pagehide', reset);
})();
