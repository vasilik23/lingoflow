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
  const levels = Array.from(document.querySelectorAll?.('[data-listening-level]') || []);
  if (levels.length) {
    const selected = document.querySelector('[data-listening-active]');
    const check = document.querySelector('[data-listening-check]');
    const sync = () => {
      const opened = levels.find(section => !section.hidden);
      levels.forEach(section => {
        section.querySelectorAll('input[type="radio"]').forEach(input => { input.disabled = section.hidden; });
        if (section.hidden) {
          if (active && section.contains(active.audio)) cancel(ui('Воспроизведение остановлено'));
          section.querySelectorAll('audio').forEach(audio => audio.pause());
        }
      });
      check.disabled = !opened;
      if (opened) selected.value = opened.id;
      document.querySelectorAll('nav.reading-audio-actions a').forEach(link => {
        if (opened && link.getAttribute('href') === '#' + opened.id) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    };
    const initial = levels.find(section => section.id === selected.value) || levels[0];
    levels.forEach(section => { section.hidden = section !== initial; });
    const openLinked = () => {
      const target = levels.find(section => '#' + section.id === window.location.hash);
      if (target) { levels.forEach(section => { section.hidden = section !== target; }); }
      sync();
    };
    selected.form.classList.add('listening-enhanced');
    document.querySelectorAll('nav.reading-audio-actions a').forEach(link => {
      link.addEventListener('click', () => {
        const target = levels.find(section => link.getAttribute('href') === '#' + section.id);
        if (!target) return;
        levels.forEach(section => { section.hidden = section !== target; });
        sync();
      });
    });
    openLinked();
    window.addEventListener('hashchange', openLinked);
  }
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
