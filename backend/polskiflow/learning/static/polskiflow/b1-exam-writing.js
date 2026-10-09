/* Local writing rehearsal: no essay submission, no exam score. */
(() => {
  const root = document.querySelector('[data-exam-writing]');
  if (!root) return;
  const ui = window.PolskiFlowI18n?.t || (text => text);
  const set = root.dataset.set;
  const key = 'lingoflow-exam-writing-v1:' + root.dataset.owner;
  const editors = [...root.querySelectorAll('[data-exam-draft]')];
  const status = root.querySelector('[data-exam-status]');
  const clock = root.querySelector('[data-exam-clock]');
  const start = root.querySelector('[data-exam-start]');
  const finish = root.querySelector('[data-exam-finish]');
  const dialog = root.querySelector('[data-exam-dialog]');
  let data = {};
  let restartPending = false;
  let storageAvailable = true;
  function read() {
    try {
      const parsed = JSON.parse(localStorage.getItem(key) || '{}');
      const clean = {};
      for (const id of ['1', '2', '3']) {
        const item = parsed?.[id];
        if (!item || !['running', 'finished'].includes(item.status) ||
            !Number.isFinite(item.deadline) || !Array.isArray(item.texts) ||
            item.texts.length !== 2 || !item.texts.every(text => typeof text === 'string')) continue;
        clean[id] = {...item, deadline: Math.min(item.deadline, Date.now() + 75 * 60000), texts: item.texts.map(text => text.slice(0, 20000))};
      }
      return clean;
    } catch (_) { storageAvailable = false; return {}; }
  }
  function save() {
    try { localStorage.setItem(key, JSON.stringify(data)); }
    catch (_) { storageAvailable = false; }
    root.querySelector('[data-exam-storage]').textContent = storageAvailable
      ? ui('Тексты и таймер хранятся только в этом браузере. В историю аккаунта этот отдельный режим не записывается.')
      : ui('Сохранение в браузере недоступно. Перед уходом скопируй оба текста; refresh потеряет попытку.');
  }
  const words = text => (text.trim().match(/\S+/gu) || []).length;
  function counts() {
    editors.forEach(editor => {
      const task = editor.closest('[data-exam-task]');
      task.querySelector('[data-exam-count]').textContent = words(editor.value) + ' / ' + task.dataset.target + ' ' + ui('слов');
    });
  }
  function activeRedirect() {
    const other = Object.entries(data).find(([id, item]) => id !== set && item.status === 'running' && item.deadline > Date.now());
    if (other) { location.replace('?set=' + other[0]); return true; }
    return false;
  }
  function render() {
    const attempt = data[set];
    const running = attempt?.status === 'running';
    const finished = attempt?.status === 'finished';
    editors.forEach(editor => { editor.disabled = !running; editor.readOnly = finished; if (finished) editor.disabled = false; });
    start.hidden = !!attempt && !restartPending;
    finish.hidden = !running;
    root.querySelector('[data-exam-result]').hidden = !finished;
    root.querySelectorAll('[data-exam-review]').forEach(panel => { panel.hidden = !finished; });
    // Lock only the set selector; normal Back and app navigation remain available.
    document.querySelectorAll('.course-levels a').forEach(link => {
      if (running) { link.setAttribute('aria-disabled', 'true'); link.tabIndex = -1; }
      else { link.removeAttribute('aria-disabled'); link.removeAttribute('tabindex'); }
    });
    if (running) status.textContent = ui('Попытка идёт. Напиши оба текста одного комплекта.');
    if (finished && !restartPending) {
      const empty = editors.filter(editor => !editor.value.trim()).length;
      status.textContent = (attempt.timedOut ? ui('Время истекло. Текущие тексты сохранены для самопроверки.') : ui('Попытка завершена. Тексты доступны для самопроверки.')) + ' ' + ui('Без ответа: ') + empty;
    }
    counts();
  }
  function end(timedOut) {
    if (data[set]?.status !== 'running') return;
    data[set].texts = editors.map(editor => editor.value);
    data[set].status = 'finished';
    data[set].timedOut = timedOut || Date.now() >= data[set].deadline;
    data[set].remaining = Math.max(0, Math.ceil((data[set].deadline - Date.now()) / 1000));
    if (dialog.open) dialog.close();
    save(); render();
  }
  function tick() {
    if (restartPending) { clock.textContent = '75:00'; return; }
    const attempt = data[set];
    if (!attempt) return;
    const seconds = attempt.status === 'finished' ? (attempt.remaining || 0) : Math.max(0, Math.ceil((attempt.deadline - Date.now()) / 1000));
    clock.textContent = Math.floor(seconds / 60).toString().padStart(2, '0') + ':' + (seconds % 60).toString().padStart(2, '0');
    if (attempt.status === 'running' && seconds === 0) end(true);
  }
  data = read();
  if (activeRedirect()) return;
  if (data[set]) editors.forEach((editor, index) => { editor.value = data[set].texts[index]; });
  save(); render(); tick();
  start.addEventListener('click', () => {
    if (storageAvailable) data = read();
    if (activeRedirect()) return;
    restartPending = false;
    data[set] = {status: 'running', deadline: Date.now() + 75 * 60000, texts: ['', ''], timedOut: false};
    editors.forEach(editor => { editor.value = ''; });
    status.textContent = ui('Попытка идёт. Напиши оба текста одного комплекта.');
    save(); render(); tick(); editors[0].focus();
  });
  editors.forEach(editor => editor.addEventListener('input', () => {
    if (data[set]?.status !== 'running') return;
    if (Date.now() >= data[set].deadline) { end(true); return; }
    data[set].texts = editors.map(item => item.value); save(); counts();
  }));
  document.querySelectorAll('.course-levels a').forEach(link => link.addEventListener('click', event => { if (data[set]?.status === 'running') event.preventDefault(); }));
  finish.addEventListener('click', () => dialog.showModal());
  root.querySelector('[data-exam-cancel]').addEventListener('click', () => dialog.close());
  root.querySelector('[data-exam-confirm]').addEventListener('click', () => end(false));
  root.querySelector('[data-exam-again]').addEventListener('click', () => {
    // Starting a new attempt is explicit; keep completed drafts until Start is pressed.
    restartPending = true; render(); clock.textContent = '75:00';
    status.textContent = ui('Нажатие «Начать 75 минут» заменит тексты этого комплекта новой попыткой.');
  });
  window.addEventListener('storage', event => {
    if (event.key !== key) return;
    restartPending = false;
    data = read();
    if (activeRedirect()) return;
    if (data[set]) editors.forEach((editor, index) => { editor.value = data[set].texts[index]; });
    render(); tick();
  });
  document.addEventListener('visibilitychange', tick);
  window.addEventListener('pageshow', tick);
  setInterval(tick, 1000);
})();
