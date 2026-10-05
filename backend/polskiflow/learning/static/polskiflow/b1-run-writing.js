(() => {
  document.querySelectorAll('[data-writing-words]').forEach(counter => {
    const editor = document.getElementById(counter.dataset.editor);
    const minimum = Number(counter.dataset.minimum), maximum = Number(counter.dataset.maximum);
    const update = () => {
      const words = editor.value.trim() ? editor.value.trim().split(/\s+/u).length : 0;
      const note = words < minimum ? 'ниже ориентира' : words > maximum ? 'выше ориентира' : 'в диапазоне';
      counter.textContent = `Слов: ${words} · ориентир ${minimum}–${maximum} · ${note}`;
    };
    editor.addEventListener('input', update);
    document.querySelector(`[data-clear-run-writing${editor.id.endsWith('-2') ? '2' : ''}]`)?.addEventListener('click', update);
    update();
  });
})();
