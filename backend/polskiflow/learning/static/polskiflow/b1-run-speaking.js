(() => {
  const ui = (typeof window !== "undefined" && window.PolskiFlowI18n?.t) || ((text, ...values) => Array.isArray(text) ? text.map((part, i) => part + (values[i] ?? "")).join("") : text);

  const root = document.querySelector('[data-b1-run]');
  const timer = root?.querySelector('[data-speaking-prep-timer]');
  if (!timer) return;
  const status = root.querySelector('[data-speaking-prep-status]');
  const endsAt = Date.now() + Number(root.dataset.preparationSeconds) * 1000;
  let disposed = false;
  const tick = () => {
    if (disposed) return;
    const left = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
    timer.textContent = `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`;
    if (left === 0) {
      root.dataset.preparingSpeaking = '0';
      root.dispatchEvent(new Event('b1-speaking-ready'));
      status.textContent = root.dataset.expired === '1' ? ui('Время части истекло.') : ui('Подготовка завершена. Ответь на три задания; запись добровольная.');
      return;
    }
    window.setTimeout(tick, 1000);
  };
  window.addEventListener('pagehide', () => { disposed = true; });
  tick();
})();
