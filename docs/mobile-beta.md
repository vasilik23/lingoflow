# Мобильная закрытая beta

В репозитории подготовлен Expo/React Native-клиент для iOS/Android.
`preview` предназначен для внутренней установки, `production` — для магазинов.
Синтетическая озвучка принята владельцем для текущего web-выпуска; это не
создаёт подписанный нативный build и не заменяет его установку на устройство.

## Подготовка выполнена · 15.10.2026

- EAS CLI закреплён на **24.14.0** в npm-команде и `eas.json`.
- `npm run verify`: конфигурация, шесть тестов готовности и TypeScript.
- `npm run build:check -- --platform ios --check-session` проверяет локальные
  условия и делает read-only `eas whoami`. Ничего не собирает, не создаёт
  облачный проект, сертификаты и не запускает публикацию.
- Код 0 означает допустимость **попытки** сборки; код 2 перечисляет недостающие
  условия. `--json` даёт машинный отчёт. Значения env, ключи, username и сырой
  вывод CLI в отчёт не попадают. Разбор ошибочного env тоже не печатает источник.
- Проверяются только `.env`, `.env.local` и текущие переменные процесса:
  `.env.local` перекрывает `.env`, переменные процесса имеют приоритет.
  Раскрытие переменных внутри значений не выполняется — нужны готовые значения.
  Удалённое EAS-окружение проверяется отдельно перед сборкой.
- На рабочей машине настроен игнорируемый `mobile/.env.local` с тремя публичными
  значениями текущего проекта. EAS ответил `Not logged in`; настоящего
  `extra.eas.projectId` пока нет. IPA/APK и build ID **не получены**.
- Проверены Metro exports: iOS — 667 модулей, Android — 665, каждый Hermes
  bundle около 2,3 MB. Артефакты в `/tmp`, не в Git. 1066 Django-тестов,
  system check и migration drift также прошли.

Проверка не подтверждает доступность API, действительность publishable key,
доступ к удалённому проекту, сертификатам или конкретному iPhone. EAS проверяет
права и подпись при сборке. JS/Metro export не является подписанным приложением.

## Однократное подключение Expo

Из `mobile/`, Node.js 24:

```bash
npm ci
npm run verify
npm run eas -- login
npm run eas -- whoami
npm run eas -- init
```

Войти нужно в аккаунт владельца проекта. Пароли, Expo/Apple токены, сертификаты
и коды MFA не присылать в чат и не коммитить. `init` выбирает/создаёт настоящий
Expo-проект и записывает его UUID в `app.json`; этот UUID нельзя заменять
придуманным. Изменение `app.json` провести через обычный PR/CI до сборки:
профиль требует зафиксированных исходников и чистого рабочего дерева.

Настроить **удалённое** окружение `preview` (локальный `.env.local` его не
создаёт). Команды используют актуальный `env:set`; `env:create` устарел:

```bash
npm run eas -- env:set preview --name EXPO_PUBLIC_API_BASE_URL --value https://lingoflow-learn.vercel.app --visibility plaintext
npm run eas -- env:set preview --name EXPO_PUBLIC_SUPABASE_URL --value https://habcghygjaynknkcbirz.supabase.co --visibility plaintext
npm run eas -- env:set preview --name EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY --visibility plaintext
```

В третьем запросе ввести только публичный publishable key из локального файла
или настроек проекта Supabase. `service_role`, database password и приватные
токены никогда не добавлять в `EXPO_PUBLIC_*`: эти значения входят в приложение.
Перед магазинным build отдельно настроить публичные значения `production`.

## Устанавливаемые внутренние сборки

После фиксации настроек и успешного preflight:

```bash
npm run build:check -- --platform android --check-session
npm run eas -- build --platform android --profile preview
```

Android `internal` собирает APK для установки. Для iPhone нужны доступ Apple
Developer, зарегистрированный UDID и ad hoc provisioning profile:

```bash
npm run eas -- device:create
npm run build:check -- --platform ios --check-session
npm run eas -- build --platform ios --profile preview
```

Первую iOS-сборку выполнять интерактивно, чтобы EAS включил зарегистрированный
телефон в provisioning profile. `preview-simulator` предназначен только для
симулятора и не устанавливается на физический iPhone. Магазинную отправку и
создание платных подписок эта инструкция автоматически не запускает.

## Приёмка нового build

Записать build ID/URL, commit, платформу, устройство/OS, дату и проверяющего.
Проверить после чистой установки:

1. Вход обычным QA-учеником, загрузку Today без токенов в сообщениях.
2. Шаг урока → завершение приложения → повторный запуск → продолжение с теми
   же шагом/счётом. Завершить урок, pull-to-refresh, сверить реальную строку.
3. Временный обрыв сети: успех показывается только после ответа сервера.
4. Изменить темы практики в web-профиле; заново открыть мобильный профиль и
   практику. Проверить чтение, сброс в mobile → web и рекомендацию навыка B2.
5. Синтетический звук, остановку, возврат из фона и системные темы/крупный текст.
6. VoiceOver/TalkBack, фокус и отсутствие обрезанных элементов.
7. Выход: Today и данные прежнего ученика недоступны; проверить смену аккаунта.

Сохранять фактические результаты. Прежняя ручная приёмка web/Safari не
объявляется приёмкой нового нативного бинарного файла.

Источники: [Expo — internal distribution](https://docs.expo.dev/build/internal-distribution/),
[EAS configuration](https://docs.expo.dev/eas/json/),
[Node.js parseEnv](https://nodejs.org/docs/latest-v24.x/api/util.html#utilparseenvcontent).
Синтаксис `whoami`, `env:set` и deprecated `env:create` проверен на CLI 24.14.0.
