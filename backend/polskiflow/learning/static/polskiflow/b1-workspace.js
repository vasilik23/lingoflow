(() => {
  const bar = document.querySelector('[data-exam-workspace]');
  if (!bar) return;
  const form = bar.closest('form');
  const root = document.querySelector('[data-b1-run], [data-simulation-root]');
  const ui = window.PolskiFlowI18n?.t || (text => text);
  const questions = Array.from(form.querySelectorAll('[data-exam-question]'));
  const missingNav = form.querySelector('[data-exam-missing]');
  const answered = question => Array.from(question.querySelectorAll('input')).some(input => input.type === 'radio' ? input.checked : input.value.trim().length > 0);
  const update = () => {
    const missing = questions.filter(question => !answered(question));
    const count = bar.querySelector('[data-exam-answered]');
    if (count) count.textContent = String(questions.length - missing.length);
    const total = bar.querySelector('[data-exam-total]');
    if (total) total.textContent = String(questions.length);
    const missingCount = form.querySelector('[data-exam-missing-count]');
    if (missingCount) missingCount.textContent = String(missing.length);
    if (missingNav) {
      missingNav.replaceChildren();
      missing.forEach(question => {
        const link = document.createElement('a');
        link.href = '#' + question.id;
        link.textContent = String(questions.indexOf(question) + 1);
        link.addEventListener('click', () => { question.focus({preventScroll: true}); });
        missingNav.appendChild(link);
      });
    }
  };
  form.addEventListener('change', update);
  form.addEventListener('input', update);
  window.addEventListener('pageshow', update);
  // Other scripts restore the owner-bound draft before this deferred update.
  window.setTimeout(update, 0);
  update();
  const dialog = form.querySelector('[data-exam-confirm]');
  if (!dialog?.showModal) return;
  let approved = false;
  let submitter = null;
  form.addEventListener('submit', event => {
    if (approved || root?.dataset.expired) return;
    const button = event.submitter;
    if (!button || (root?.dataset.phase && root.dataset.phase !== 'part')) return;
    const action = button.value;
    if (action && !['finish', 'skip'].includes(action)) return;
    event.preventDefault();
    // A cancelled finish must not stop audio or mark the draft as intentionally left.
    event.stopImmediatePropagation();
    submitter = button;
    const description = dialog.querySelector('[data-exam-confirm-description]');
    description.textContent = action === 'skip'
      ? ui('Эта часть останется без балла. Ответы этой части не будут проверены.')
      : ui('После проверки изменить ответы этой части уже нельзя.');
    dialog.showModal();
  }, true);
  dialog.querySelector('[data-exam-cancel]').addEventListener('click', () => dialog.close());
  dialog.querySelector('[data-exam-accept]').addEventListener('click', () => {
    if (root?.dataset.expired && questions.length) { dialog.close(); return; }
    approved = true;
    dialog.close();
    form.requestSubmit(submitter);
    approved = false;
  });
  root?.addEventListener('b1-run-expired', () => { if (dialog.open) dialog.close(); });
})();
