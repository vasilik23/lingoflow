(() => {
  const ui = window.PolskiFlowI18n?.t || ((text, ...values) => Array.isArray(text) ? text.map((part, i) => part + (values[i] ?? '')).join('') : text);
  const supported = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
  let active = null;
  const players = [];
  const cancel = message => {
    window.PolskiFlowAudioSession?.stopSpeech?.();
    if (active) {
      clearTimeout(active.timer);
      active.utterance.onstart = active.utterance.onend = active.utterance.onerror = null;
      active.status.textContent = message;
      active.stop.disabled = true;
      active = null;
    }
    if (supported) speechSynthesis.cancel();
  };
  for (const name of ['dialogue', 'b1', 'b2']) {
    const player = document.querySelector('[data-' + name + '-player]');
    if (!player) continue;
    const status = player.querySelector('[data-' + name + '-status]');
    if (!supported) {
      // The transcript remains available even without browser speech support.
      player.hidden = false;
      status.textContent = ui('Не удалось запустить системный польский голос');
      player.querySelectorAll('button, select').forEach(control => { control.disabled = true; });
      continue;
    }
    player.hidden = false;
    const linesId = name === 'dialogue' ? 'listening-dialogue-lines' : name + '-listening-lines';
    const lines = JSON.parse(document.getElementById(linesId).textContent);
    const repeat = player.querySelector('[data-' + name + '-repeat]');
    const stop = player.querySelector('[data-listening-stop]');
    const rate = player.querySelector('[data-' + name + '-rate]');
    let lastText = lines.join(' ');
    players.push({status, stop});
    const speak = (text, label) => {
      cancel(ui('Воспроизведение остановлено'));
      lastText = text;
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'pl-PL';
      utterance.rate = Number(rate.value);
      const attempt = {utterance, status, stop, timer: null};
      active = attempt;
      status.textContent = ui('Подготавливаем системный польский голос…');
      repeat.disabled = false;
      stop.disabled = false;
      const finish = message => {
        if (active !== attempt) return;
        clearTimeout(attempt.timer);
        status.textContent = message;
        stop.disabled = true;
        utterance.onstart = utterance.onend = utterance.onerror = null;
        active = null;
      };
      utterance.onstart = () => {
        if (active !== attempt) return;
        clearTimeout(attempt.timer);
        status.textContent = name === 'dialogue' ? ui('Воспроизведение: ') + label : ui('Воспроизведение записи ' + name.toUpperCase());
      };
      utterance.onend = () => finish(name === 'dialogue' ? ui('Прослушано: ') + label : ui('Запись ' + name.toUpperCase() + ' прослушана'));
      utterance.onerror = () => finish(ui('Не удалось запустить системный польский голос'));
      attempt.timer = setTimeout(() => {
        if (active === attempt) cancel(ui('Не удалось запустить системный польский голос'));
      }, 10000);
      try {
        window.PolskiFlowAudioSession?.prepareSpeech(utterance);
        // Keep this synchronous with the learner's tap for Safari.
        speechSynthesis.speak(utterance);
      } catch (_) { cancel(ui('Не удалось запустить системный польский голос')); }
    };
    player.querySelector('[data-' + name + '-play]').addEventListener('click', () => speak(lines.join(' '), ui('весь диалог')));
    repeat.addEventListener('click', () => speak(lastText, ui('последний фрагмент')));
    stop.addEventListener('click', () => cancel(ui('Воспроизведение остановлено')));
    player.querySelectorAll('[data-dialogue-fragment]').forEach(button => {
      button.addEventListener('click', () => {
        const index = Number(button.dataset.dialogueFragment);
        speak(lines[index], ui`фрагмент ${index + 1}`);
      });
    });
  }
  window.addEventListener('pagehide', () => {
    cancel(ui('Готово к воспроизведению'));
    players.forEach(({status, stop}) => {
      status.textContent = ui('Готово к воспроизведению');
      stop.disabled = true;
    });
  });
})();
