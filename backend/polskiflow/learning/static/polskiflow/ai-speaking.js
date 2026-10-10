(() => {
  const panel = document.querySelector('[data-ai-speaking]');
  const button = panel?.querySelector('[data-ai-transcribe]');
  if (!button) return;
  const recorder = panel.closest('[data-run-recorder]');
  const consent = panel.querySelector('[data-ai-audio-consent]');
  const confirmed = panel.querySelector('[data-ai-confirmed]');
  const status = panel.querySelector('[data-transcribe-status]');
  const editor = document.getElementById('speech-transcript');
  const textPanel = panel.querySelector('[data-speech-text]');
  const ui = window.PolskiFlowI18n?.t || (text => text);
  let clip = null, controller = null;
  const resetText = () => {
    panel.dataset.aiToken = ''; editor.value = ''; confirmed.checked = false;
    editor.dispatchEvent(new Event('input', {bubbles: true})); textPanel.hidden = true;
  };
  const cancel = () => { controller?.abort(); controller = null; button.disabled = !clip; };
  recorder.addEventListener('b1-recording-cleared', () => {
    clip = null; cancel(); resetText(); consent.checked = false;
    status.textContent = ui('Сначала запиши и останови устный ответ.');
  });
  recorder.addEventListener('b1-recording-ready', event => {
    cancel(); resetText(); consent.checked = false; clip = event.detail.blob;
    button.disabled = false; status.textContent = ui('Запись готова. Расшифровка начнётся только по твоему выбору.');
  });
  editor.addEventListener('input', () => { confirmed.checked = false; });
  consent.addEventListener('change', () => { if (!consent.checked) { cancel(); status.textContent = ''; } });
  button.addEventListener('click', async () => {
    if (controller || !clip) return;
    if (!consent.checked) { status.textContent = ui('Сначала разреши отправку записи в Groq.'); return; }
    if (!clip.size || clip.size > 2 * 1024 * 1024) { status.textContent = ui('Для расшифровки нужна запись MP4, WebM или Ogg размером до 2 МБ.'); return; }
    const csrf = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    if (!csrf) { status.textContent = ui('Обнови страницу перед проверкой текста.'); return; }
    resetText(); controller = new AbortController(); const current = controller;
    button.disabled = true; status.textContent = ui('Распознаём польскую речь…');
    const timeout = setTimeout(() => current.abort(), 30000);
    const data = new FormData(); data.append('token', panel.dataset.aiRecordingToken); data.append('consent', 'true'); data.append('audio', clip, 'answer');
    let serviceError = '';
    try {
      const response = await fetch(panel.dataset.transcribeUrl, {method: 'POST', credentials: 'same-origin', redirect: 'error', headers: {'X-CSRFToken': csrf}, body: data, signal: current.signal});
      const payload = await response.json();
      if (controller !== current) return;
      if (!response.ok) { serviceError = payload.error || ui('ИИ речи временно недоступен. Запись и самопроверка доступны без отправки.'); throw new Error('service'); }
      editor.value = payload.text; panel.dataset.aiToken = payload.token; textPanel.hidden = false;
      confirmed.checked = false; status.textContent = ui('Расшифровка готова. Проверь её перед разбором.'); editor.focus();
    } catch (error) {
      if (controller === current) status.textContent = serviceError || ui('Не удалось расшифровать запись. Она осталась на странице; попробуй позже.');
    } finally {
      clearTimeout(timeout); if (controller === current) { controller = null; button.disabled = !clip; }
    }
  });
  window.addEventListener('pagehide', () => { clip = null; cancel(); resetText(); });
})();
