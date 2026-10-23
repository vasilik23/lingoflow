# Проверка доставки штатного GitHub alert

Ручной workflow `Alert Delivery Test` создаёт один намеренно красный запуск.
Он не обращается к production, Supabase или почтовому API, не делает checkout,
не получает secrets и не имеет прав GITHUB_TOKEN. GitHub может отправить
обычное уведомление о неуспешном workflow согласно настройкам получателя.

Сам красный запуск не подтверждает доставку. Чтобы закрыть этот шаг, оператор
должен подтвердить получение и время; email не включать в отчёт. Этот тест
не проверяет отдельный внешний paging channel и не заменяет проверку
production-smoke.

## Порядок

1. Получить явное согласие оператора на одно тестовое уведомление.
2. В GitHub Settings → Notifications проверить Actions, канал и адрес
   получения. Действующая подписка или HTTP 404 API не доказывают доставку.
   Настройки получателя этот workflow не изменяет.
3. Открыть Actions → Alert Delivery Test → Run workflow на `main`.
   Выбрать `SEND_TEST_ALERT`. Значение по умолчанию `DO_NOT_SEND` пропускает job.
   Запуски на другой ветке также пропускаются.
4. При разрешении оператора допустим CLI:

   ```sh
   gh workflow run alert-delivery-test.yml --ref main -f confirmation=SEND_TEST_ALERT
   ```

5. Дождаться ровно одного ожидаемого failure. Сохранить ссылку, source SHA,
   время запуска и результат. Не перезапускать автоматически, если письмо
   не пришло: проверить настройки, затем отдельно согласовать новый тест.
6. Получить подтверждение оператора: канал и время фактического получения.
   Если подтверждения нет, delivery остаётся `unverified`.

Ожидаемый failure этого workflow не означает сбой приложения. Настоящий
`Production Smoke` сохраняет обычное поведение: его ошибки не подавляются
и не превращаются в зелёный результат.

## Текущий статус

**Done · 23 октября 2026.** Оператор вручную запустил один разрешённый тест
и подтвердил: отправлено в 10:11, получено в 10:11 (Europe/Warsaw, UTC+02:00).
Канал отдельно не указан; факт получения подтверждён оператором.

- [GitHub Actions run 39922870416](https://github.com/vasilik23/lingoflow/actions/runs/39922870416).
- Создан: 2026-10-23 08:11:07 UTC (10:11:07 Europe/Warsaw).
- Source SHA: `da9f61a73fd3d083bec7036f09aea72b398de43e`.
- Статус API: `completed / failure` — ожидаемый намеренный отказ.
- Проверен ровно один запуск. Повторная отправка не требуется.

Предшествующая автоматическая попытка не выполнила dispatch: CLI завис,
его процессы остановлены; прямое чтение API вернуло 401 до отправки.
Публичный GitHub API после ручного запуска подтвердил указанный run и SHA.

Приёмка штатного уведомления завершена по подтверждению оператора.
Отдельный внешний paging channel этим не проверен; приёмку остальных
направлений широкого запуска этот тест не заменяет.

Основание:
[GitHub: notifications for workflow runs](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/notifications-for-workflow-runs),
[GitHub: manually running a workflow](https://docs.github.com/en/actions/managing-workflow-runs/manually-running-a-workflow).
