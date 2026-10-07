(() => {
  const ui = (typeof window !== "undefined" && window.PolskiFlowI18n?.t) || ((text, ...values) => Array.isArray(text) ? text.map((part, i) => part + (values[i] ?? "")).join("") : text);

  const main = document.querySelector('[data-b1-run], [data-b1-listening]');
  if (!main) return;
  let stopActive = null;
  const players = main.dataset.multiListening ? Array.from(document.querySelectorAll('[data-run-listening-block]')) : [main];
  players.forEach(root => {
  const play = root?.querySelector('[data-run-play]');
  if (!play) return;
  const stop = root.querySelector('[data-run-audio-stop]');
  const status = root.querySelector('[data-run-audio-status]');
  const audio = root.querySelector('audio[data-run-audio]');
  if (root.dataset.missingRecording === '1') {
    play.disabled = true; stop.disabled = true;
    status.textContent = ui('Запись этого прогона недоступна. Можно пропустить часть или начать новый прогон.');
    return;
  }
  const key = `polskiflow-b1-run-listening:${root.dataset.namespace}${root.dataset.blockId ? `:${root.dataset.blockId}` : ""}`;
  const limit = 2, pauseMs = 30000;
  let state = {runId: root.dataset.runId, used: 0, cooldownUntil: 0};
  let unavailableStorage = false;
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) || 'null');
    if (saved?.runId === state.runId && Number.isInteger(saved.used) && saved.used >= 0 && saved.used <= limit && Number.isFinite(saved.cooldownUntil)) {
      state = saved;
    }
  } catch (_) { unavailableStorage = true; }
  let busy = false, started = false, expired = root.dataset.expired === '1', disposed = false;
  let utterance = null, watchdog = null;
  let attempt = 0;
  const save = () => {
    try { sessionStorage.setItem(key, JSON.stringify(state)); }
    catch (_) { unavailableStorage = true; }
  };
  const update = () => {
    const left = Math.max(0, Math.ceil((state.cooldownUntil - Date.now()) / 1000));
    play.disabled = busy || expired || disposed || state.used >= limit || left > 0;
    stop.disabled = !busy;
    play.textContent = busy ? ui('Воспроизводится…') : left && state.used < limit ? ui`Повтор через ${left} с` : ui`Прослушать · осталось ${limit - state.used} из ${limit}`;
  };
  const settled = (message) => {
    if (!busy) return;
    clearTimeout(watchdog); busy = false;
    if (started) state.cooldownUntil = Date.now() + pauseMs;
    save(); update();
    if (!disposed) status.textContent = message + (unavailableStorage ? ui(' Счётчик не сохранится при перезагрузке: хранилище браузера недоступно.') : '');
  };
  const cancel = (message) => {
    attempt++;
    settled(message);
    if (audio) { audio.pause(); audio.currentTime = 0; }
    if ('speechSynthesis' in window) speechSynthesis.cancel();
  };
  if (audio) {
    audio.addEventListener('playing', () => {
      if (!busy || disposed || expired || started) return;
      started = true; clearTimeout(watchdog); state.used++; state.cooldownUntil = Date.now() + pauseMs; save(); update();
      status.textContent = ui`Прослушивание ${state.used} из ${limit}. Остановка тоже расходует прослушивание.`;
    });
    audio.addEventListener('ended', () => settled(state.used < limit ? ui('Сообщение завершено. Перед повтором — пауза 30 секунд для ответов.') : ui('Два прослушивания использованы. Ответь на вопросы.')));
    audio.addEventListener('error', () => cancel(started ? ui('Запись прервана; начатое прослушивание учтено.') : ui('Запись не запустилась; прослушивание не потрачено. Попробуй ещё раз или пропусти часть.')));
  }
  play.addEventListener('click', () => {
    if (busy || expired || disposed || state.used >= limit || Date.now() < state.cooldownUntil) return;
    stopActive?.();
    stopActive = () => { if (busy) cancel(ui('Воспроизведение остановлено. Начатое прослушивание учтено; перед повтором — пауза 30 секунд.')); };
    if (audio) {
      busy = true; started = false; update();
      status.textContent = ui('Подготавливаем аудиозапись…');
      const currentAttempt = ++attempt;
      watchdog = setTimeout(() => { if (!started && currentAttempt === attempt) cancel(ui('Запись не запустилась; прослушивание не потрачено. Можно попробовать ещё раз.')); }, 10000);
      try {
        audio.currentTime = 0;
        const promise = audio.play();
        promise?.catch(() => { if (currentAttempt === attempt) cancel(ui('Запись недоступна; прослушивание не потрачено. Попробуй ещё раз или пропусти часть.')); });
      } catch (_) { cancel(ui('Запись недоступна; прослушивание не потрачено.')); }
      return;
    }
    if (!('speechSynthesis' in window) || !window.SpeechSynthesisUtterance) {
      status.textContent = ui('Системный голос недоступен. Можно пропустить аудирование без балла.'); return;
    }
    busy = true; started = false; update();
    status.textContent = ui('Подготавливаем системный польский голос…');
    utterance = new SpeechSynthesisUtterance(JSON.parse(document.getElementById(main.dataset.listeningTranscript || 'run-listening-transcript').textContent));
    const current = utterance;
    current.lang = 'pl-PL'; current.rate = .9;
    current.onstart = () => {
      if (!busy || disposed || expired || current !== utterance || started) return;
      started = true; clearTimeout(watchdog); state.used++; state.cooldownUntil = Date.now() + pauseMs; save(); update();
      status.textContent = ui`Прослушивание ${state.used} из ${limit}. Остановка тоже расходует прослушивание.`;
    };
    current.onend = () => { if (current === utterance) settled(state.used < limit ? ui('Сообщение завершено. Перед повтором — пауза 30 секунд для ответов.') : ui('Два прослушивания использованы. Ответь на вопросы.')); };
    current.onerror = () => { if (current === utterance) settled(started ? ui('Воспроизведение прервано; начатое прослушивание учтено.') : ui('Голос не запустился; прослушивание не потрачено. Попробуй ещё раз или пропусти часть.')); };
    watchdog = setTimeout(() => { if (!started && current === utterance) cancel(ui('Голос не запустился; прослушивание не потрачено. Можно попробовать ещё раз.')); }, 10000);
    try { speechSynthesis.speak(current); }
    catch (_) { cancel(ui('Системный голос недоступен; прослушивание не потрачено.')); }
  });
  stop.addEventListener('click', () => cancel(ui('Воспроизведение остановлено. Начатое прослушивание учтено; перед повтором — пауза 30 секунд.')));
  main.addEventListener('b1-run-expired', () => { expired = true; cancel(ui('Время части истекло. Можно пропустить её без балла.')); update(); });
  const leave = () => { disposed = true; cancel(''); update(); };
  document.getElementById(main.dataset.listeningForm || 'b1-run-form').addEventListener('submit', leave);
  window.addEventListener('pagehide', leave);
  const tick = () => { if (disposed) return; update(); setTimeout(tick, 1000); };
  save(); tick();
  });
})();
