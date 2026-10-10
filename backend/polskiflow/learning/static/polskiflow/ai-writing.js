(() => {
  const ui = window.PolskiFlowI18n?.t || (text => text);
  const labels = {content: 'Выполнение задания', structure: 'Структура и стиль', grammar: 'Грамматика', vocabulary: 'Словарь'};
  const csrf = () => document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
  document.querySelectorAll('[data-ai-writing]').forEach(panel => {
    const button = panel.querySelector('[data-ai-submit]');
    if (!button) return;
    const editor = document.getElementById(panel.dataset.aiEditor);
    const consent = panel.querySelector(panel.dataset.aiSpeech ? '[data-ai-confirmed]' : '[data-ai-consent]');
    const status = panel.querySelector('[data-ai-status]');
    const result = panel.querySelector('[data-ai-result]');
    let pending = false, controller;
    const clear = () => {
      controller?.abort(); controller = undefined; pending = false; button.disabled = false;
      result.replaceChildren(); result.hidden = true; status.textContent = '';
    };
    editor.addEventListener('input', clear);
    if (panel.dataset.aiSpeech) consent.addEventListener('change', () => { if (!consent.checked) clear(); });
    // Clear stale feedback when the local draft is explicitly deleted.
    const container = panel.closest('[data-writing-prompt]') || panel.parentElement;
    container.querySelectorAll('[data-reset-draft], [data-clear-run-writing], [data-clear-run-writing2]').forEach(reset => reset.addEventListener('click', () => {
      if (!editor.value) clear();
    }));
    button.addEventListener('click', async () => {
      if (pending) return;
      if (!consent.checked) { status.textContent = panel.dataset.aiSpeech ? ui('Проверь расшифровку и подтверди отправку текста в Groq.') : ui('Сначала разреши отправку текста в Groq.'); return; }
      if (panel.dataset.aiSpeech && !panel.dataset.aiToken) { status.textContent = ui('Сначала расшифруй запись.'); return; }
      const text = editor.value;
      if (!text.trim() || text.length > 6000) { status.textContent = ui('Для проверки напиши от 1 до 6000 символов.'); return; }
      const token = csrf();
      if (!token) { status.textContent = ui('Обнови страницу перед проверкой текста.'); return; }
      pending = true; button.disabled = true; result.hidden = true;
      controller = new AbortController();
      const current = controller;
      status.textContent = ui('ИИ проверяет текст…');
      const timeout = setTimeout(() => current.abort(), 30000);
      try {
        const response = await fetch(panel.dataset.aiUrl, {
          method: 'POST', credentials: 'same-origin', redirect: 'error', signal: current.signal,
          headers: {'Content-Type': 'application/json', 'X-CSRFToken': token},
          body: JSON.stringify({token: panel.dataset.aiToken, text, consent: true, ...(panel.dataset.aiSpeech ? {confirmed: true} : {})}),
        });
        const payload = await response.json();
        if (current !== controller || editor.value !== text) return;
        if (!response.ok) throw new Error(payload.error || ui('ИИ временно недоступен или квота исчерпана. Черновик остался в редакторе; продолжи самопроверку.'));
        const review = payload.result;
        result.replaceChildren();
        const append = (tag, content, target = result) => {
          const node = document.createElement(tag); node.textContent = content; target.append(node); return node;
        };
        append('h3', ui('Учебная оценка ИИ') + ` · ${review.score}/${review.maximum}`);
        append('p', panel.dataset.aiSpeech ? ui('Это разбор подтверждённой расшифровки. Произношение не оценивается.') : ui('Это оценка текущего текста, не официальный балл B1.'));
        Object.entries(labels).forEach(([key, label]) => {
          const item = review.criteria[key];
          append('h4', ui(label) + ` · ${item.score}/5`);
          append('p', item.feedback);
        });
        append('h4', ui('Ошибки и исправления'));
        if (!review.errors.length) append('p', ui('ИИ не выделил конкретных ошибок. Перечитай текст самостоятельно.'));
        review.errors.forEach(error => {
          const item = append('div', '');
          append('p', error.quote + ' → ' + error.correction, item).lang = 'pl';
          append('p', error.explanation, item);
        });
        append('h4', ui('Следующий шаг')); append('p', review.next_step);
        result.hidden = false; status.textContent = ui('Разбор готов. Он исчезнет при изменении текста или уходе со страницы.');
      } catch (error) {
        if (current === controller) status.textContent = error.name === 'AbortError'
          ? ui('Проверка прервана. Черновик остался в редакторе.')
          : error.message === 'Failed to fetch' || error instanceof SyntaxError
            ? ui('Не удалось проверить текст. Черновик остался в редакторе; попробуй позже.') : error.message;
      } finally {
        clearTimeout(timeout);
        if (current === controller) { pending = false; button.disabled = false; }
      }
    });
  });
})();
