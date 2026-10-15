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

    let currentSaved = false;
    let needsAttention = false;
    let flushing = false;
    let queue;
    try { queue = queueApi.createQueue({
      onStatus: function (event) {
        // Queue-wide status and another lesson's acknowledgement cannot prove
        // that the result displayed on this card reached the account.
        if (currentSaved || event.state === "synced") return;
        if (event.eventId && event.eventId !== payload.event_id && event.state !== "auth-required") return;
        if (needsAttention && !event.eventId) return;
        if (event.state === "needs-attention") needsAttention = true;
        status.textContent = messageFor(event.state);
        if (event.state === "sent" && event.eventId === payload.event_id) {
          currentSaved = true;
          const card = panel.closest(".complete-card");
          // A newer successful attempt may already have cancelled this weak
          // result's repeat. An event receipt is not a current-plan receipt.
          const followup = card?.querySelector("[data-followup-pending]");
          if (followup) {
            followup.textContent = ui("Результат сохранён. Открой план, чтобы увидеть актуальные повторения.");
            followup.removeAttribute("hidden");
          }
        }
        retry.hidden = currentSaved || needsAttention;
      },
    }); } catch (error) {
      status.textContent = ui("Локальное сохранение недоступно. Вернись к уроку позже.");
      return;
    }

    async function flush() {
      if (flushing) return;
      flushing = true;
      retry.disabled = true;
      if (!currentSaved && !needsAttention) status.textContent = ui("Отправляем сохранённый результат…");
      try { await queue.flushSession(namespace, csrfToken); }
      catch (error) { if (!currentSaved && !needsAttention) status.textContent = ui("Нет соединения. Результат остаётся в этом браузере."); }
      retry.disabled = false;
      flushing = false;
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
  document.addEventListener("htmx:afterSwap", function (event) { scan(event.target); });
}());
