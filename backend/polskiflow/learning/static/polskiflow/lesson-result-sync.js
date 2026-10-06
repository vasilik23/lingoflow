(function () {
  const ui = (typeof window !== "undefined" && window.PolskiFlowI18n?.t) || ((text, ...values) => Array.isArray(text) ? text.map((part, i) => part + (values[i] ?? "")).join("") : text);

  "use strict";

  function messageFor(state) {
    if (state === "sent" || state === "synced") return ui("Результат сохранён.");
    if (state === "auth-required") return ui("Войди снова, затем повтори отправку.");
    if (state === "needs-attention") return ui("Результат требует проверки. Попробуй ещё раз позже.");
    if (state === "retry-paused") return ui("Автоматические попытки приостановлены.");
    return ui("Результат сохранён в этом браузере и ожидает отправки.");
  }

  async function init(panel) {
    if (panel.dataset.syncReady) return;
    panel.dataset.syncReady = "true";
    const status = panel.querySelector("[data-sync-status]");
    const retry = panel.querySelector("[data-sync-retry]");
    const queueApi = window.PolskiFlowResultQueue;
    if (!queueApi) {
      status.textContent = ui("Локальное сохранение недоступно. Вернись к уроку позже.");
      return;
    }

    const namespace = panel.dataset.queueNamespace;
    const csrfToken = panel.dataset.csrfToken;
    let payload;
    try { payload = JSON.parse(panel.dataset.resultPayload); }
    catch (error) {
      status.textContent = ui("Не удалось подготовить результат к отправке.");
      return;
    }

    const queue = queueApi.createQueue({
      onStatus: function (event) {
        status.textContent = messageFor(event.state);
        retry.hidden = event.state === "sent" || event.state === "synced";
      },
    });

    async function flush() {
      retry.disabled = true;
      status.textContent = ui("Отправляем сохранённый результат…");
      try { await queue.flushSession(namespace, csrfToken); }
      catch (error) { status.textContent = ui("Нет соединения. Результат остаётся в этом браузере."); }
      retry.disabled = false;
    }

    retry.addEventListener("click", flush);
    window.addEventListener("online", flush);
    try {
      await queue.enqueue(namespace, payload);
      retry.hidden = false;
      await flush();
    } catch (error) {
      status.textContent = ui("Локальное сохранение недоступно. Вернись к уроку позже.");
    }
  }

  function scan(root) {
    root.querySelectorAll?.("[data-lesson-result-sync]").forEach(init);
  }
  scan(document);
}());
