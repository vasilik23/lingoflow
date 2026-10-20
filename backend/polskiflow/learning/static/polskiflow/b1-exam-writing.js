/* Local writing rehearsal: no essay submission, no exam score. */
(() => {
  const root = document.querySelector('[data-exam-writing]');
  if (!root) return;
  const ui = window.PolskiFlowI18n?.t || (text => text);
  const set = root.dataset.set;
  const key = 'lingoflow-exam-writing-v1:' + root.dataset.owner;
  const editors = [...root.querySelectorAll('[data-exam-draft]')];
  const status = root.querySelector('[data-exam-status]');
  const idleStatus = status.textContent;
  const clock = root.querySelector('[data-exam-clock]');
  const start = root.querySelector('[data-exam-start]');
  const finish = root.querySelector('[data-exam-finish]');
  const dialog = root.querySelector('[data-exam-dialog]');
  const historyStatus = root.querySelector('[data-exam-history-status]');
  const historyRetry = root.querySelector('[data-exam-history-retry]');
  // One immutable metadata entry per owner/attempt, independent of editor slots.
  const queuePrefix = 'lingoflow-exam-writing-history-v1:' + root.dataset.owner + ':';
  const memoryQueue = new Map();
  const sending = new Set();
  const fields = ['attempt_id', 'set_id', 'content_version', 'started_at', 'finished_at', 'timed_out', 'remaining_seconds', 'words_a', 'words_b'];
  function safeSummary(payload) {
    if (!payload || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(payload.attempt_id) ||
        !['1', '2', '3'].includes(payload.set_id) || payload.content_version !== 1 ||
        !['started_at', 'finished_at'].every(k => typeof payload[k] === 'string' && Number.isFinite(Date.parse(payload[k]))) ||
        typeof payload.timed_out !== 'boolean' || !Number.isInteger(payload.remaining_seconds) ||
        payload.remaining_seconds < 0 || payload.remaining_seconds > 4500 ||
        ![payload.words_a, payload.words_b].every(n => Number.isInteger(n) && n >= 0 && n <= 20000)) return null;
    return Object.fromEntries(fields.map(k => [k, payload[k]]));
  }
  function enqueue(payload) {
    const clean = safeSummary(payload);
    if (!clean) return;
    const value = JSON.stringify(clean);
    memoryQueue.set(clean.attempt_id, clean);
    try { localStorage.setItem(queuePrefix + clean.attempt_id, value); }
    catch (_) { storageAvailable = false; }
  }
  function queued() {
    const entries = new Map(memoryQueue);
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const name = localStorage.key(i);
        if (!name?.startsWith(queuePrefix)) continue;
        try {
          const clean = safeSummary(JSON.parse(localStorage.getItem(name)));
          if (clean && name === queuePrefix + clean.attempt_id) entries.set(clean.attempt_id, clean);
        } catch (_) { /* Ignore malformed local entries. */ }
      }
    } catch (_) { storageAvailable = false; }
    return [...entries.values()];
  }
  let data = {};
  let restartPending = false;
  let storageAvailable = true;
  function replaceDrafts(texts) {
    editors.forEach((editor, index) => {
      editor.value = texts?.[index] || '';
      editor.dispatchEvent(new Event('lingoflow:writing-reset'));
    });
    root.querySelectorAll('[data-exam-result] input[type="checkbox"]').forEach(input => { input.checked = false; });
  }
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
        // Persisted browser data is untrusted: never forward arbitrary keys or texts.
        const payload = item.historyPayload;
        delete clean[id].historyPayload;
        if (item.status === 'finished' && payload && payload.attempt_id === item.attemptId &&
            /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(item.attemptId) &&
            payload.set_id === id && payload.content_version === 1 &&
            typeof payload.started_at === 'string' && Number.isFinite(Date.parse(payload.started_at)) &&
            typeof payload.finished_at === 'string' && Number.isFinite(Date.parse(payload.finished_at)) &&
            typeof payload.timed_out === 'boolean' &&
            Number.isInteger(payload.remaining_seconds) && payload.remaining_seconds >= 0 && payload.remaining_seconds <= 4500 &&
            [payload.words_a, payload.words_b].every(value => Number.isInteger(value) && value >= 0 && value <= 20000)) {
          clean[id].historyPayload = Object.fromEntries(['attempt_id', 'set_id', 'content_version', 'started_at', 'finished_at', 'timed_out', 'remaining_seconds', 'words_a', 'words_b'].map(name => [name, payload[name]]));
        }
      }
      return clean;
    } catch (_) { storageAvailable = false; return {}; }
  }
  function save() {
    try { localStorage.setItem(key, JSON.stringify(data)); }
    catch (_) { storageAvailable = false; }
    root.querySelector('[data-exam-storage]').textContent = storageAvailable
      ? ui('Тексты и таймер хранятся в этом браузере. В аккаунт отправляется только сводка завершённой попытки, без текстов.')
      : ui('Сохранение в браузере недоступно. Перед уходом скопируй оба текста; refresh потеряет попытку.');
  }
  const words = text => (text.trim().match(/\S+/gu) || []).length;
  function historyRender() {
    const attempt = data[set];
    if (!historyStatus || !historyRetry) return;
    const pending = queued();
    historyRetry.hidden = pending.length === 0;
    historyRetry.disabled = pending.length > 0 && pending.every(item => sending.has(item.attempt_id));
    if (pending.length) {
      historyStatus.textContent = ui('Ожидают отправки: ') + pending.length;
      return;
    }
    if (attempt?.status !== 'finished') { historyStatus.textContent = ''; return; }
    historyStatus.textContent = !attempt.historyPayload
      ? ui('Эта старая попытка доступна только в браузере; сводка в аккаунт не отправляется.')
      : attempt.historySaved ? ui('Сводка попытки сохранена в аккаунте. Тексты не отправлялись.')
      : sending.has(attempt.attemptId) ? ui('Сохраняем сводку попытки в аккаунт…')
      : ui('Сводка пока не сохранена в аккаунте. Проверь соединение и повтори отправку; тексты остаются в браузере.');
  }
  async function sendSummary(summary) {
    const id = summary.attempt_id;
    if (sending.has(id)) return;
    const payload = JSON.stringify(summary);
    sending.add(id); historyRender();
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(root.dataset.historyUrl || '/writing/exam/b1/history/', {
        method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-LingoFlow-Writing-Owner': root.dataset.owner,
          'X-CSRFToken': document.querySelector('[name="csrfmiddlewaretoken"]')?.value || ''},
        body: payload, signal: controller.signal,
      });
      const result = await response.json();
      if (!response.ok || result.saved !== true || result.attempt_id !== id) throw Error('Not saved');
      // ACK removes only this immutable entry; another editor/attempt is untouched.
      const latest = storageAvailable ? read() : data;
      for (const item of Object.values(latest)) {
        if (item.attemptId === id && JSON.stringify(item.historyPayload) === payload) item.historySaved = true;
      }
      data = latest; save();
      if (localStorage.getItem(queuePrefix + id) === payload) localStorage.removeItem(queuePrefix + id);
      memoryQueue.delete(id);
    } catch (_) { /* Keep metadata queued until an acknowledged idempotent save. */ }
    finally { window.clearTimeout(timeout); sending.delete(id); historyRender(); }
  }
  function syncHistory() {
    historyRender();
    return Promise.all(queued().map(sendSummary));
  }
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
    if (!attempt) status.textContent = idleStatus;
    if (finished && !restartPending) {
      const empty = editors.filter(editor => !editor.value.trim()).length;
      status.textContent = (attempt.timedOut ? ui('Время истекло. Текущие тексты сохранены для самопроверки.') : ui('Попытка завершена. Тексты доступны для самопроверки.')) + ' ' + ui('Без ответа: ') + empty;
    }
    counts();
    historyRender();
  }
  function end(timedOut) {
    if (data[set]?.status !== 'running') return;
    data[set].texts = editors.map(editor => editor.value);
    data[set].status = 'finished';
    data[set].timedOut = timedOut || Date.now() >= data[set].deadline;
    data[set].remaining = Math.max(0, Math.ceil((data[set].deadline - Date.now()) / 1000));
    const attempt = data[set];
    if (attempt.attemptId && Number.isFinite(attempt.startedAt)) {
      attempt.historyPayload = {
        attempt_id: attempt.attemptId, set_id: set, content_version: 1,
        started_at: new Date(attempt.startedAt).toISOString(),
        finished_at: new Date(Math.min(Date.now(), attempt.deadline)).toISOString(),
        timed_out: attempt.timedOut, remaining_seconds: Math.min(4500, attempt.remaining),
        words_a: Math.min(20000, words(attempt.texts[0])), words_b: Math.min(20000, words(attempt.texts[1])),
      };
    }
    if (attempt.historyPayload) enqueue(attempt.historyPayload);
    if (dialog.open) dialog.close();
    save(); render();
    syncHistory();
  }
  function tick() {
    if (restartPending) { clock.textContent = '75:00'; return; }
    const attempt = data[set];
    if (!attempt) { clock.textContent = '75:00'; return; }
    const seconds = attempt.status === 'finished' ? (attempt.remaining || 0) : Math.max(0, Math.ceil((attempt.deadline - Date.now()) / 1000));
    clock.textContent = Math.floor(seconds / 60).toString().padStart(2, '0') + ':' + (seconds % 60).toString().padStart(2, '0');
    if (attempt.status === 'running' && seconds === 0) end(true);
  }
  data = read();
  // Migrate unsent summaries from the previous editor-coupled format.
  Object.values(data).forEach(item => { if (item.historyPayload && !item.historySaved) enqueue(item.historyPayload); });
  syncHistory();
  if (activeRedirect()) return;
  if (data[set]) replaceDrafts(data[set].texts);
  save(); render(); tick();
  syncHistory();
  historyRetry?.addEventListener('click', syncHistory);
  start.addEventListener('click', () => {
    if (storageAvailable) data = read();
    if (activeRedirect()) return;
    restartPending = false;
    const startedAt = Date.now();
    data[set] = {status: 'running', deadline: startedAt + 75 * 60000, texts: ['', ''], timedOut: false, startedAt, attemptId: window.crypto?.randomUUID?.()};
    replaceDrafts(['', '']);
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
  window.addEventListener('online', syncHistory);
  window.addEventListener('storage', event => {
    if (event.key?.startsWith(queuePrefix)) { syncHistory(); return; }
    if (event.key !== key && event.key !== null) return;
    const previous = JSON.stringify(data[set]);
    const draftIdentity = item => JSON.stringify(item && [item.attemptId, item.startedAt, item.deadline, item.status, item.texts]);
    const previousDraft = draftIdentity(data[set]);
    data = read();
    if (activeRedirect()) return;
    if (previous === JSON.stringify(data[set]) && event.key !== null) return;
    if (previousDraft !== draftIdentity(data[set]) || event.key === null) {
      restartPending = false;
      replaceDrafts(data[set]?.texts);
    }
    render(); tick();
    syncHistory();
  });
  document.addEventListener('visibilitychange', tick);
  window.addEventListener('pageshow', tick);
  setInterval(tick, 1000);
})();
