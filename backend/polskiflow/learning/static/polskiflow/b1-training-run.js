(() => {
  const root = document.querySelector('[data-b1-run]');
  if (!root) return;
  const form = document.getElementById('b1-run-form');
  const token = form.querySelector('[name="run_token"]');
  const key = `polskiflow-b1-run:${root.dataset.namespace}`;
  const writing = document.getElementById('run-writing');
  const fields = Array.from(form.querySelectorAll('input[type="radio"], input[type="checkbox"]'));
  const storageStatus = root.querySelector('[data-run-storage-status]');
  let savedWriting = '';
  let intentionalLeave = false;
  const clear = () => { try { sessionStorage.removeItem(key); sessionStorage.removeItem(`polskiflow-b1-run-listening:${root.dataset.namespace}`); } catch (_) {} };
  if (root.dataset.phase === 'report') {
    try { sessionStorage.removeItem(`polskiflow-b1-run-listening:${root.dataset.namespace}`); } catch (_) {}
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
    fields.forEach(input => { input.checked = draft.answers?.[input.name] === input.value; });
    if (writing && typeof draft.writing === 'string') writing.value = draft.writing;
  }
  const save = () => {
    const answers = {};
    fields.forEach(input => { if (input.checked) answers[input.name] = input.value; });
    try {
      sessionStorage.setItem(key, JSON.stringify({token: token.value, answers, writing: writing?.value || ''}));
      savedWriting = writing?.value || '';
      storageStatus.hidden = true;
    } catch (_) {
      storageStatus.hidden = false;
      storageStatus.textContent = 'Браузер не сохранил прогресс. Не перезагружай страницу; скопируй текст перед уходом.';
    }
  };
  form.addEventListener('change', save);
  writing?.addEventListener('input', save);
  root.querySelector('[data-clear-run-writing]')?.addEventListener('click', () => {
    writing.value = ''; save(); writing.focus();
  });
  root.querySelector('[data-restart-run]').addEventListener('click', () => { intentionalLeave = true; clear(); });
  form.addEventListener('submit', () => { intentionalLeave = true; save(); });
  window.addEventListener('beforeunload', event => {
    if (!intentionalLeave && writing?.value && writing.value !== savedWriting) {
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
      const left = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
      timer.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
      if (left === 0) {
        if (root.dataset.phase === 'break') {
          root.querySelector('[data-next-part]').disabled = false;
          timerStatus.textContent = 'Перерыв завершён. Можно начать следующую часть.';
        } else {
          root.dataset.expired = '1';
          root.dispatchEvent(new Event('b1-run-expired'));
          root.querySelector('[data-finish-part]').disabled = true;
          fields.forEach(input => { input.disabled = true; });
          if (writing) writing.disabled = true;
          root.querySelector('[data-run-play]')?.setAttribute('disabled', '');
          if ('speechSynthesis' in window) speechSynthesis.cancel();
          timerStatus.textContent = 'Время истекло. Можно пропустить часть без балла.';
        }
        return;
      }
      if (previous > 60 && left <= 60) timerStatus.textContent = 'Осталась одна минута.';
      previous = left;
      window.setTimeout(tick, 1000);
    };
    tick();
  }
})();
