(() => {
  const ui = window.PolskiFlowI18n?.t || ((text, ...values) => Array.isArray(text) ? text.map((part, i) => part + (values[i] ?? '')).join('') : text);
  let active = null;
  const players = [];
  const unavailable = () => ui('Не удалось воспроизвести аудио. Попробуй ещё раз.');
  const cancel = message => {
    if (!active) return;
    const attempt = active;
    active = null;
    clearTimeout(attempt.timer);
    attempt.audio.onplaying = attempt.audio.onended = attempt.audio.onerror = null;
    attempt.audio.pause();
    attempt.audio.removeAttribute('src');
    attempt.audio.load();
    attempt.audio.remove();
    attempt.status.textContent = message;
    attempt.stop.disabled = true;
  };
  for (const name of ['dialogue', 'b1', 'b2']) {
    const player = document.querySelector('[data-' + name + '-player]');
    if (!player) continue;
    const status = player.querySelector('[data-' + name + '-status]');
    const clips = JSON.parse(document.getElementById(player.dataset.mediaId).textContent);
    player.hidden = false;
    if (!clips.full) {
      status.textContent = unavailable();
      player.querySelectorAll('button, select').forEach(control => { control.disabled = true; });
      continue;
    }
    const repeat = player.querySelector('[data-' + name + '-repeat]');
    const stop = player.querySelector('[data-listening-stop]');
    const rate = player.querySelector('[data-' + name + '-rate]');
    let lastPart = 'full';
    players.push({status, stop});
    const play = (part, label) => {
      cancel(ui('Воспроизведение остановлено'));
      lastPart = part;
      const audio = document.createElement('audio');
      audio.hidden = true;
      audio.setAttribute('data-practice-audio', '');
      audio.src = clips[part];
      audio.playbackRate = Number(rate.value);
      player.append(audio);
      const attempt = {audio, status, stop, timer: null};
      active = attempt;
      status.textContent = ui('Аудио загружается…');
      repeat.disabled = false;
      stop.disabled = false;
      audio.onplaying = () => {
        if (active !== attempt) return;
        clearTimeout(attempt.timer);
        status.textContent = name === 'dialogue' ? ui('Воспроизведение: ') + label : ui('Воспроизведение записи ' + name.toUpperCase());
      };
      audio.onended = () => {
        if (active !== attempt) return;
        cancel(name === 'dialogue' ? ui('Прослушано: ') + label : ui('Запись ' + name.toUpperCase() + ' прослушана'));
      };
      audio.onerror = () => { if (active === attempt) cancel(unavailable()); };
      attempt.timer = setTimeout(() => { if (active === attempt) cancel(unavailable()); }, 10000);
      try {
        window.PolskiFlowAudioSession?.prepare(audio);
        audio.play()?.catch(() => { if (active === attempt) cancel(unavailable()); });
      } catch (_) { cancel(unavailable()); }
    };
    player.querySelector('[data-' + name + '-play]').addEventListener('click', () => play('full', ui('весь диалог')));
    repeat.addEventListener('click', () => play(lastPart, ui('последний фрагмент')));
    stop.addEventListener('click', () => cancel(ui('Воспроизведение остановлено')));
    player.querySelectorAll('[data-dialogue-fragment]').forEach(button => {
      button.addEventListener('click', () => {
        const index = Number(button.dataset.dialogueFragment);
        play('fragment-' + index, ui`фрагмент ${index + 1}`);
      });
    });
  }
  window.addEventListener('pagehide', () => {
    cancel(ui('Готово к воспроизведению'));
    players.forEach(({status, stop}) => { status.textContent = ui('Готово к воспроизведению'); stop.disabled = true; });
  });
})();
