# Первая iOS Simulator-сборка · 9 ноября 2026

EAS завершил внутреннюю сборку **FINISHED**, профиль `preview-simulator`:

- [Страница сборки](https://expo.dev/accounts/vasilik23s-team/projects/vasilik23/builds/a1fcdf60-a0a7-4dfc-8c18-c5d74c48d5f7).
- [Скачать архив приложения](https://expo.dev/artifacts/eas/XH2pLiULoWia7nZaQLzAMdoPAfKwAcNOBuH3o-g4-Ug.tar.gz).
- Build ID `a1fcdf60-a0a7-4dfc-8c18-c5d74c48d5f7`.
- Source commit `2fb202f4f6e431d2f767d0e6b2efb4bf3b67aa2a`.
- Версия `1.0.0`, build number `1`, bundle ID `com.lingoflow.mobile`.
- Создан 9 ноября 14:58:48 UTC, завершён 15:02:11 UTC.
- EAS подтверждает `platform=IOS`, `distribution=INTERNAL`, `isForIosSimulator=true`.

Мобильное дерево Git `94514ab04e97331b53b38b03efe9f74d973dbdab`
совпадает с деревом исходников Android APK от 29 октября. Между ними менялись
backend/документы; мобильные исходники не обновлялись. Это две платформенные
сборки одного мобильного кода, а не приёмка одинакового нативного поведения.

## Проверка архива

Архив скачан, полностью прочитан tar и распакован в отдельную временную папку.
Проверено отсутствие абсолютных и родительских путей в списке файлов.
Параметры из Info.plist: `DTPlatformName=iphonesimulator`,
`CFBundleSupportedPlatforms=[iPhoneSimulator]`, minimum OS **16.4**.
Исполняемый файл — Mach-O universal, **arm64 и x86_64**.

Размер архива **16 085 693 байта**, 101 запись.
SHA-256: `258082f247e616e06ae48c0a5d18a1068c79d69bac90c4f9a09334286dee069a`.
Локальный архив: `/private/tmp/lingoflow-ios-simulator-1.0.0-1.tar.gz`.
Результат проверки: `/private/tmp/lf-ios-artifact-verification.json`.
Архив, app bundle и служебные ответы EAS в Git не добавляются.

Перед сборкой проверены чистая рабочая копия, связанный проект и совпадение
трёх публичных preview env с удалёнными значениями. Ключ не выводился и не
добавлялся в Git. Production/store-окружение не изменялось; Apple-подпись для
физического устройства и submission не запускались.

## Запуск: пока не выполнен

На текущем Mac установлен только CommandLineTools: `xcrun simctl` недоступен.
Read-only `eas simulator:availability --json` вернул `available=false` для
`vasilik23s-team`. Облачная сессия не создавалась, подписка и waitlist не менялись.
Поэтому запуск, вход, Today, урок, SecureStore, TTS, темы и доступность
в iOS Simulator **не проверены**. Статус FINISHED подтверждает сборку.

На Mac с установленным Xcode и совместимым iOS Simulator из `mobile/`:

```bash
npm run eas -- build:run --id a1fcdf60-a0a7-4dfc-8c18-c5d74c48d5f7 --platform ios
```

Команда проверена по `eas build:run --help` закреплённого CLI 24.14.0.
После запуска пройти сценарии из [приёмки build](mobile-beta.md#приёмка-нового-build).
Архив симулятора не устанавливается на физический iPhone. Для него остаются
отдельная device-сборка, подпись и регистрация устройства.

Проверки исходников: **32 мобильных теста**, TypeScript и config check,
**1230 Django-тестов**, system check, migration drift и diff check прошли.
Новых вызовов Groq, записей учебного прогресса и изменений базы не было.

Основание профиля: [Expo — Build for iOS Simulators](https://docs.expo.dev/build-reference/simulators/).
Доступность cloud runtime определяется аккаунтом; [Expo описывает ограниченный
доступ к Simulators](https://docs.expo.dev/agentic-workflows/introduction/).
