(() => {
  const ui = (typeof window !== "undefined" && window.PolskiFlowI18n?.t) || ((text, ...values) => Array.isArray(text) ? text.map((part, i) => part + (values[i] ?? "")).join("") : text);

  document.querySelectorAll('[data-writing-words]').forEach(counter => {
    const editor = document.getElementById(counter.dataset.editor);
    const minimum = Number(counter.dataset.minimum), maximum = Number(counter.dataset.maximum);
    const update = () => {
      const words = editor.value.trim() ? editor.value.trim().split(/\s+/u).length : 0;
      const note = words < minimum ? ui('ниже ориентира') : words > maximum ? ui('выше ориентира') : ui('в диапазоне');
      counter.textContent = ui`Слов: ${words} · ориентир ${minimum}–${maximum} · ${note}`;
    };
    editor.addEventListener('input', update);
    document.querySelector(`[data-clear-run-writing${editor.id.endsWith('-2') ? '2' : ''}]`)?.addEventListener('click', update);
    update();
  });
})();
