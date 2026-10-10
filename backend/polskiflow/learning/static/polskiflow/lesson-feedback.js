/* Focus the freshly rendered lesson explanation after an answer. */
(() => {
  function focusFeedback(root) {
    const feedback = root.matches?.('[data-lesson-feedback]')
      ? root : root.querySelector?.('[data-lesson-feedback]');
    if (!feedback || feedback.dataset.feedbackFocused) return;
    feedback.dataset.feedbackFocused = 'true';
    feedback.focus();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => focusFeedback(document));
  } else {
    focusFeedback(document);
  }
  document.addEventListener('htmx:afterSettle', event => focusFeedback(event.target));
})();
