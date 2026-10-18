/* Review presentation only: never changes signed answers, scores or run state. */
(() => {
  document.querySelectorAll('[data-run-review]').forEach(review => {
    const controls = review.querySelector('[data-review-filters]');
    if (!controls) return;
    const answers = [...review.querySelectorAll('[data-review-answer]')];
    const buttons = [...controls.querySelectorAll('[data-review-filter]')];
    const empty = review.querySelector('[data-review-empty]');
    buttons.forEach(button => {
      const filter = button.dataset.reviewFilter;
      const count = answers.filter(answer => filter === 'all' || answer.dataset.reviewAnswer === filter).length;
      button.append(document.createTextNode(` · ${count}`));
      button.addEventListener('click', () => {
        answers.forEach(answer => { answer.hidden = filter !== 'all' && answer.dataset.reviewAnswer !== filter; });
        buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        empty.hidden = count !== 0;
      });
    });
    controls.hidden = false;
    review.querySelectorAll('[data-review-source-link]').forEach(link => link.addEventListener('click', event => {
      const target = document.getElementById(link.hash.slice(1));
      if (!target || !review.contains(target)) return;
      event.preventDefault();
      target.open = true;
      target.scrollIntoView({block: 'start'});
      target.querySelector('summary')?.focus({preventScroll: true});
    }));
  });
})();
