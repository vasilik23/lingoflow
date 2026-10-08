(() => {
  const ui = (typeof window !== "undefined" && window.PolskiFlowI18n?.t) || ((text, ...values) => Array.isArray(text) ? text.map((part, i) => part + (values[i] ?? "")).join("") : text);

  const root = document.querySelector('[data-b1-run]');
  if (!root) return;
  const form = document.getElementById('b1-run-form');
  const token = form.querySelector('[name="run_token"]');
  const key = `polskiflow-b1-run:${root.dataset.namespace}`;
  const writing = document.getElementById('run-writing');
  const writing2 = document.getElementById('run-writing-2');
  const writingSnapshot = () => JSON.stringify([writing?.value || '', writing2?.value || '']);
  const fields = Array.from(form.querySelectorAll('input[type="radio"], input[type="checkbox"]:not([data-ai-consent]), input[data-run-written]'));
  const storageStatus = root.querySelector('[data-run-storage-status]');
  let savedWriting = '';
  let intentionalLeave = false;
  const clearListening = () => {
    try {
      const prefix = `polskiflow-b1-run-listening:${root.dataset.namespace}`;
      sessionStorage.removeItem(prefix);
      for (let i = sessionStorage.length - 1; i >= 0; i--) {
        const item = sessionStorage.key(i);
        if (item?.startsWith(prefix + ':')) sessionStorage.removeItem(item);
      }
    } catch (_) {}
  };
  const clear = () => { try { sessionStorage.removeItem(key); clearListening(); } catch (_) {} };
  if (root.dataset.phase === 'report') {
    clearListening();
  }
  const url = new URL(window.location.href);
  if (url.searchParams.get('restart') === '1' || root.dataset.discard) {
    clear(); url.searchParams.delete('restart'); window.history.replaceState({}, '', url);
  }
  let draft = null;
  try { draft = JSON.parse(sessionStorage.getItem(key) || 'null'); } catch (_) {}
  if (root.dataset.fresh && draft && typeof draft.token === 'string' && draft.token.length <= 16384) {
    token.value = draft.token;
    const action = document.createElement('input');
    action.type = 'hidden'; action.name = 'action'; action.value = 'resume';
    form.appendChild(action); form.submit(); return;
  }
  if (draft?.token === token.value) {
    fields.forEach(input => { if (input.matches('[data-run-written]')) input.value = typeof draft.answers?.[input.name] === 'string' ? draft.answers[input.name].slice(0, 120) : ''; else input.checked = draft.answers?.[input.name] === input.value; });
    if (writing && typeof draft.writing === 'string') writing.value = draft.writing;
    if (writing2 && typeof draft.writing2 === 'string') writing2.value = draft.writing2;
  }
  const save = () => {
    const answers = {};
    fields.forEach(input => { if (input.checked || input.matches('[data-run-written]')) answers[input.name] = input.value; });
    try {
      sessionStorage.setItem(key, JSON.stringify({token: token.value, answers, writing: writing?.value || '', writing2: writing2?.value || ''}));
      savedWriting = writingSnapshot();
      storageStatus.hidden = true;
    } catch (_) {
      storageStatus.hidden = false;
      storageStatus.textContent = ui('Браузер не сохранил прогресс. Не перезагружай страницу; скопируй текст перед уходом.');
    }
  };
  form.addEventListener('change', save);
  fields.filter(input => input.matches('[data-run-written]')).forEach(input => input.addEventListener('input', save));
  writing?.addEventListener('input', save);
  writing2?.addEventListener('input', save);
  root.querySelector('[data-clear-run-writing]')?.addEventListener('click', () => {
    writing.value = ''; save(); writing.focus();
  });
  root.querySelector('[data-clear-run-writing2]')?.addEventListener('click', () => {
    writing2.value = ''; save(); writing2.focus(); writing2.dispatchEvent(new Event('input', {bubbles: true}));
  });
  root.querySelector('[data-restart-run]').addEventListener('click', () => { intentionalLeave = true; clear(); });
  form.addEventListener('submit', () => { intentionalLeave = true; save(); });
  window.addEventListener('beforeunload', event => {
    if (!intentionalLeave && (writing?.value || writing2?.value) && writingSnapshot() !== savedWriting) {
      event.preventDefault(); event.returnValue = '';
    }
  });
  save();
  // Refresh must replay resume, never the previous start/finish operation.
  // Only navigate once the new signed state has been safely saved in this tab.
  if (root.dataset.normalizeNavigation && storageStatus.hidden) {
    window.location.replace(url); return;
  }
  const timer = root.querySelector('[data-run-timer]');
  const timerStatus = root.querySelector('[data-run-timer-status]');
  const endsAt = Date.now() + Number(root.dataset.seconds) * 1000;
  let previous = Number(root.dataset.seconds);
  if (timer) {
    const tick = () => {
      if (root.dataset.expired) return;
      const left = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
      timer.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
      if (left === 0) {
        if (root.dataset.phase === 'break') {
          root.querySelector('[data-next-part]').disabled = false;
          timerStatus.textContent = ui('Перерыв завершён. Можно начать следующую часть.');
        } else {
          save();
          const snapshot = fields.filter(input => input.name.startsWith('answer_') && (input.checked || input.matches('[data-run-written]'))).map(input => ({name: input.name, value: input.value}));
          root.dataset.expired = '1';
          root.dispatchEvent(new Event('b1-run-expired'));
          const objective = root.dataset.mode === 'objective';
          root.querySelector('[data-finish-part]').disabled = objective;
          fields.forEach(input => { input.disabled = input.name !== 'reviewed'; });
          if (writing) writing.disabled = true;
          if (writing2) writing2.disabled = true;
          root.querySelector('[data-run-play]')?.setAttribute('disabled', '');
          if ('speechSynthesis' in window) speechSynthesis.cancel();
          if (objective) {
            // Disabled controls are omitted by HTML forms. Freeze the exact
            // current answers as hidden fields before submitting the timeout.
            snapshot.forEach(answer => {
              const input = document.createElement('input');
              input.type = 'hidden'; input.name = answer.name; input.value = answer.value;
              form.appendChild(input);
            });
            const action = document.createElement('input');
            action.type = 'hidden'; action.name = 'action'; action.value = 'timeout';
            form.appendChild(action);
            form.noValidate = true;
            timerStatus.textContent = ui('Время истекло. Проверяем текущие ответы; незаполненные считаются пропущенными.');
            if (form.requestSubmit) form.requestSubmit(); else form.submit();
          } else {
            timerStatus.textContent = ui('Время истекло. Заверши самопроверку или пропусти часть.');
          }
        }
        return;
      }
      if (previous > 60 && left <= 60) timerStatus.textContent = ui('Осталась одна минута.');
      previous = left;
      window.setTimeout(tick, 1000);
    };
    tick();
    document.addEventListener?.('visibilitychange', () => { if (!document.hidden && !root.dataset.expired) tick(); });
  }
})();
