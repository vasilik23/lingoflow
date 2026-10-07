# LingoFlow: аудит названия и адресов

Основной адрес: https://lingoflow-learn.vercel.app
Репозиторий: https://github.com/vasilik23/lingoflow
Локальная рабочая папка: `Documents/lingoflow`.

Проверены отслеживаемые файлы web/backend, мобильного приложения, документации,
CI, локальных app-конфигураций и навыков разработки. Кэши зависимостей и Git-
история не являются текущим брендингом и не переписываются.

## Обновлено

- Пользовательские web-названия, RU/PL/EN, PWA и значок — LingoFlow.
- Expo name/slug, схема `lingoflow`, будущие iOS/Android IDs `com.lingoflow.mobile`.
  Store-сборки ещё не опубликованы; это настройка будущих сборок.
- npm-пакет `lingoflow-mobile` и Python distribution `lingoflow`.
- Vercel-проект `lingoflow-learn`, production-ссылки и scheduled smoke.
- GitHub `vasilik23/lingoflow`, origin, ссылки на PR, локальный проект.
- Имена в документации и описаниях; новые оригинальные манифесты принимают
  `created_for: LingoFlow` наряду с прежним значением.

## Совместимость

| Старое имя | Почему сохранено |
| --- | --- |
| Python package `backend/polskiflow` и static namespace | Стабильные импорты, migrations и пути ресурсов. Массовое переименование отклонено автоматической проверкой риска; это не пользовательское название. |
| JS `PolskiFlow*`, cookies, ключи local/session/secure storage, signing salts | Существующие сессии, черновики, настройки и подписанные состояния должны продолжать читаться. |
| Expo scheme `polskiflow` | Дополнительная схема для старых глубоких ссылок; основная схема — `lingoflow`. |
| `created_for: PolskiFlow`, исторические лицензии и provenance | Фактическое авторство ранее опубликованного контента и порядок production migrations не переписываются. |
| Идентификаторы навыков `.codex/skills/polskiflow-*` | Стабильные ссылки каталога инструментов; описания используют LingoFlow. |
| Старый локальный backend-путь SDK | Совместимая ссылка на действующий venv, пока PyCharm держит старый SDK в памяти; основной репозиторий находится в `lingoflow`. |

## Старые ссылки

GET/HEAD браузерных страниц на прежних production-доменах возвращают 308 на
новый адрес, сохраняя путь и query. Браузер сохраняет fragment при переходе,
если Location не задаёт другой fragment. Preview-домены не перенаправляются.
POST, API, static, health/ready, manifest и service worker остаются доступны
для существующих клиентов. Cookies привязаны к домену: на новом адресе нужен
повторный вход; токены через URL не переносятся.

Supabase email-callback gateway остаётся `https://polish-learn.vercel.app`:
это ранее используемый redirect origin. Подтверждение email и восстановление
пароля переходят через его совместимый redirect на новый адрес. После
обновления provider allowlist можно задать `AUTH_EMAIL_CALLBACK_ORIGIN`
новому origin; до этого рабочая схема не требует изменения Auth-конфигурации.
