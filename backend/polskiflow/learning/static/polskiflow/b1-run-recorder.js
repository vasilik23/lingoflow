(() => {
  const panel = document.querySelector('[data-run-recorder]');
  if (!panel) return;
  const root = document.querySelector('[data-b1-run]');
  const form = document.getElementById('b1-run-form');
  const start = panel.querySelector('[data-record-start]');
  const stop = panel.querySelector('[data-record-stop]');
  const remove = panel.querySelector('[data-record-delete]');
  const audio = panel.querySelector('audio');
  const status = panel.querySelector('[data-record-status]');
  const finish = root.querySelector('[data-finish-part]');
  let stream = null;
  let recorder = null;
  let audioUrl = null;
  let pending = false;
  let recordingBusy = false;
  let disposed = false;
  let expired = root.dataset.expired === '1';
  let preparing = root.dataset.preparingSpeaking === '1';
  const active = () => recorder && recorder.state !== 'inactive';
  const release = () => {
    stream?.getTracks().forEach(track => track.stop());
    stream = null;
  };
  const clearClip = () => {
    audio.pause(); audio.removeAttribute('src'); audio.load();
    audio.hidden = true; remove.hidden = true;
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    audioUrl = null;
  };
  const update = () => {
    start.disabled = pending || recordingBusy || preparing || expired || disposed;
    stop.disabled = !active();
    finish.disabled = pending || recordingBusy || preparing || expired;
  };
  const stopRecording = () => {
    if (active()) { try { recorder.stop(); } catch (_) {} }
    release();
  };
  const cleanup = () => {
    disposed = true; stopRecording(); clearClip(); update();
  };
  start.addEventListener('click', async () => {
    if (pending || recordingBusy || preparing || expired || disposed) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      status.textContent = 'Запись недоступна в этом браузере. Можно ответить вслух без записи.';
      return;
    }
    clearClip(); pending = true; update();
    status.textContent = 'Ожидаем разрешение на микрофон…';
    try {
      stream = await navigator.mediaDevices.getUserMedia({audio: true});
      if (disposed || expired) { release(); return; }
      recorder = new MediaRecorder(stream);
      recordingBusy = true;
      const recording = recorder;
      const chunks = [];
      let failed = false;
      recording.addEventListener('dataavailable', event => { if (!disposed && event.data.size) chunks.push(event.data); });
      recording.addEventListener('error', () => {
        failed = true; stopRecording(); update();
        status.textContent = 'Не удалось записать ответ. Можно продолжить без записи.';
      });
      recording.addEventListener('stop', () => {
        release(); recordingBusy = false; update();
        if (disposed || failed) return;
        if (!chunks.length) { status.textContent = 'Запись пуста. Можно попробовать ещё раз.'; return; }
        const blob = new Blob(chunks, {type: recording.mimeType || chunks[0].type});
        audioUrl = URL.createObjectURL(blob); audio.src = audioUrl;
        audio.hidden = false; remove.hidden = false;
        status.textContent = expired
          ? 'Время истекло, микрофон выключен. Можно прослушать запись перед пропуском части.'
          : 'Микрофон выключен. Прослушай ответ и выполни самопроверку.';
        if (!expired) audio.focus();
      });
      stream.getTracks().forEach(track => track.addEventListener('ended', stopRecording));
      recording.start();
      status.textContent = 'Ответ записывается только на этом устройстве.';
    } catch (_) {
      release(); recorder = null; recordingBusy = false;
      if (!disposed) status.textContent = 'Микрофон недоступен или разрешение не получено. Можно продолжить без записи.';
    } finally {
      pending = false; update();
    }
  });
  stop.addEventListener('click', stopRecording);
  remove.addEventListener('click', () => { clearClip(); status.textContent = 'Запись удалена. Аудио нигде не сохранено.'; });
  root.addEventListener('b1-run-expired', () => {
    expired = true; stopRecording(); update();
  });
  root.addEventListener('b1-speaking-ready', () => { preparing = false; update(); });
  form.addEventListener('submit', cleanup);
  root.querySelector('[data-restart-run]').addEventListener('click', cleanup);
  window.addEventListener('pagehide', cleanup);
  update();
})();
