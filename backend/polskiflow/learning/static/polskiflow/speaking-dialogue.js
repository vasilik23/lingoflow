/* Sequential, learner-confirmed oral replies; no recognition or audio upload. */
(() => {
  const ui = window.PolskiFlowI18n?.t || (text => text);
  const run = document.querySelector('[data-b1-run]');
  document.querySelectorAll('[data-speaking-dialogue]').forEach(root => {
    const turns = [...root.querySelectorAll('[data-dialogue-turn]')];
    const next = root.querySelector('[data-dialogue-next]');
    const restart = root.querySelector('[data-dialogue-restart]');
    const status = root.querySelector('[data-dialogue-status]');
    const key = 'lingoflow-speaking-dialogue-v1:' + root.dataset.dialogueOwner + ':' + root.dataset.dialogueId;
    let step = 0;
    let unavailable = false;
    try {
      const saved = JSON.parse(sessionStorage.getItem(key) || 'null');
      if (saved && saved.expires > Date.now() && Number.isInteger(saved.step) && saved.step >= 0 && saved.step <= turns.length) step = saved.step;
    } catch (_) { unavailable = true; }
    const save = () => {
      try { sessionStorage.setItem(key, JSON.stringify({step, expires: Date.now() + 4 * 3600000})); }
      catch (_) { unavailable = true; }
    };
    const blocked = () => run && (run.dataset.preparingSpeaking === '1' || run.dataset.expired === '1');
    const render = () => {
      turns.forEach((turn, index) => { turn.hidden = index > step; turn.classList.toggle('is-current', index === step); });
      next.hidden = step === turns.length;
      restart.hidden = step !== turns.length || !!run;
      next.disabled = !!blocked();
      if (step === turns.length) status.textContent = ui('Диалог завершён. Проверь, ответил ли ты на все реплики и задал ли свой вопрос.');
      else if (blocked()) status.textContent = ui('Реплики можно продолжить после подготовки, пока идёт время части.');
      else status.textContent = ui('Ответь на текущую реплику вслух.');
      if (unavailable) status.textContent += ' ' + ui('Браузер не сохранил шаг диалога. После refresh он начнётся заново.');
    };
    next.addEventListener('click', () => {
      if (blocked() || step >= turns.length) return;
      step += 1; save(); render();
      const current = turns[step];
      if (current) { current.tabIndex = -1; current.focus({preventScroll: true}); }
    });
    restart.addEventListener('click', () => { step = 0; save(); render(); next.focus(); });
    if (run) {
      run.addEventListener('b1-speaking-ready', render);
      run.addEventListener('b1-run-expired', render);
      // Resume uses form.submit() and keeps the step; explicit finish/restart clears it.
      run.querySelector('form')?.addEventListener('submit', () => { try { sessionStorage.removeItem(key); } catch (_) {} });
      run.querySelector('[data-restart-run]')?.addEventListener('click', () => { try { sessionStorage.removeItem(key); } catch (_) {} });
    }
    render();
  });
})();
