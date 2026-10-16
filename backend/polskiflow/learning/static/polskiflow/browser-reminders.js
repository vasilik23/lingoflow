/* Foreground-only, owner-scoped reminder. No system permission or background timer. */
(function () {
  "use strict";
  const root = document.querySelector('[data-browser-reminder]');
  if (!root) return;
  const owner = root.dataset.namespace;
  const key = `lingoflow-reminder:${owner}`;
  const panel = root.querySelector('[data-reminder-panel]');
  const toggle = root.querySelector('[data-reminder-toggle]');
  const status = root.querySelector('[data-reminder-status]');
  let active = true;
  let busy = false;
  let controller;
  const supported = !!navigator.locks;
  function read() {
    const data = JSON.parse(localStorage.getItem(key) || '{}');
    return {enabled: data.enabled === true, day: typeof data.day === 'string' ? data.day : ''};
  }
  function write(data) { localStorage.setItem(key, JSON.stringify(data)); }
  function hide() { if (panel) panel.hidden = true; }
  function controls() {
    if (!toggle) return;
    try {
      const enabled = read().enabled;
      // Verify storage is writable before presenting this device as available.
      write(read());
      toggle.disabled = !supported;
      toggle.textContent = enabled ? root.dataset.disable : root.dataset.enable;
      status.textContent = !supported ? root.dataset.unavailable : enabled ? root.dataset.on : root.dataset.off;
    } catch (_) {
      toggle.disabled = true;
      status.textContent = root.dataset.unavailable;
    }
  }
  if (toggle) toggle.addEventListener('click', async () => {
    try {
      await navigator.locks.request(key, () => {
        const data = read();
        write({...data, enabled: !data.enabled});
      });
    } catch (_) { /* Storage or lock unavailable: stay disabled. */ }
    controls();
  });
  root.querySelector('[data-reminder-dismiss]')?.addEventListener('click', hide);
  async function check() {
    if (!panel || !active || busy || document.visibilityState !== 'visible') return;
    busy = true;
    try {
      if (!supported || !read().enabled) { hide(); return; }
      await navigator.locks.request(key, {ifAvailable: true}, async (lock) => {
        if (!lock || !active || document.visibilityState !== 'visible' || !read().enabled) return;
        controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        const started = performance.now();
        let data;
        try {
          const response = await fetch(root.dataset.endpoint, {
            credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: controller.signal,
            headers: {'Accept': 'application/json'}
          });
          if (!response.ok) throw new Error('Unavailable');
          data = await response.json();
        } finally { clearTimeout(timeout); }
        const state = read();
        if (!active || document.visibilityState !== 'visible' || !state.enabled || performance.now() - started > 5000
            || data.namespace !== owner || data.channel !== 'today_foreground'
            || !/^\d{4}-\d{2}-\d{2}$/.test(data.day) || data.due !== true) {
          hide(); return;
        }
        if (state.day === data.day) return;
        // Claim before display, under a cross-tab lock. Storage failure means no reminder.
        write({...state, day: data.day});
        panel.hidden = false;
      });
    } catch (_) { hide(); }
    finally { busy = false; }
  }
  document.addEventListener('visibilitychange', () => {
    hide();
    controller?.abort();
    if (document.visibilityState === 'visible') check();
  });
  window.addEventListener('storage', (event) => {
    if (event.key === key || event.key === null) { hide(); controls(); }
  });
  window.addEventListener('pagehide', () => { active = false; hide(); controller?.abort(); });
  window.addEventListener('pageshow', () => { active = true; check(); });
  controls();
  check();
  setInterval(check, 60000);
}());
