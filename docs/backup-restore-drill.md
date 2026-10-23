# Supabase Free: копия и локальный restore drill

Инструмент `ops/backup-drill.mjs` проверяет целостность подготовленной копии
и выполняет импорт только в пустой локальный Supabase через `127.0.0.1`.
Он не создаёт копию сам, не подключается к production и не разрешает удалённый
restore. Успешный импорт ещё не означает успешную приёмку восстановления.

15 октября подготовлены инструмент и десять автоматических проверок его границ.
18 октября выполнен настоящий read-only capture production: роли, схема и данные
сохранены в локальный зашифрованный том; SHA-256 проверены до и после повторного
открытия тома. Завершены импорт в disposable Supabase и функциональная приёмка:
69 таблиц, 12 последовательностей, права и RLS, настоящий Auth, страницы и экспорт.
[Capture](backup-capture-2026-10-18.md) ·
[приёмка восстановления](backup-restore-acceptance-2026-10-18.md).

## 1. Снять копию

Использовать доверенную операторскую машину с зашифрованным рабочим томом, Docker и
Supabase CLI **2.120.0**. Сначала проверить `supabase --version` и
`supabase db dump --help`. Установку системных инструментов этот скрипт не выполняет.
Для команд `--linked` CLI должен быть связан с проектом `habcghygjaynknkcbirz`;
проверить `supabase/.temp/project-ref`. Не переключать проект вслепую.
Альтернатива — явный `--db-url` без пароля в URL, с проверенным project ref
и паролем через защищённое окружение. Capture 18 октября использовал этот вариант.

Создать новый каталог вне репозитория, за пределами общих/sync-папок:

```sh
umask 077
mkdir -m 700 /private/tmp/lingoflow-db-drill
```

Пароль БД вводить через поддерживаемый CLI защищённый prompt или локальную
переменную `SUPABASE_DB_PASSWORD` при отключённом shell tracing. Не добавлять
connection string с паролем в командную строку, Git, CI или чат. Из корня проекта:

```sh
supabase db dump --linked --file /private/tmp/lingoflow-db-drill/roles.sql --role-only
supabase db dump --linked --file /private/tmp/lingoflow-db-drill/schema.sql
supabase db dump --linked --file /private/tmp/lingoflow-db-drill/data.sql --use-copy --data-only
node ops/backup-drill.mjs seal /private/tmp/lingoflow-db-drill
node ops/backup-drill.mjs verify /private/tmp/lingoflow-db-drill
```

Перед `seal` проверить успешные exit codes всех трёх dump-команд. Не допускать
DDL/migrations между schema и data dump; три отдельных файла не являются одним
общим snapshot. Зафиксировать начало/конец capture отдельно: `sealed_at` — время
контрольной суммы, а не гарантированная дата восстановления или RPO.

`seal` требует непустые обычные файлы `0600`, каталог `0700` вне репозитория,
запрещает symlink/hardlink файлов и перезапись manifest. Manifest содержит только
project ref, время и SHA-256/размер каждого файла. `verify` выявляет изменение
после sealing, но не удостоверяет происхождение или SQL-полноту архива.
Нельзя восстанавливать полученный от постороннего SQL даже с совпавшим manifest.

Архив содержит персональные данные и Auth-данные. Права файлов не являются
шифрованием. До хранения вне этой машины зашифровать копию утверждённым
оператором средством, проверить расшифровку, разместить вне исходного диска
и согласовать срок удаления. Не загружать копию в GitHub artifacts или отчёт.
Каталог `/private/tmp` предназначен для drill, а не долговременного хранения.

## 2. Восстановить в изолированный локальный Supabase

Подготовить новый disposable Supabase с совместимыми Postgres **17**, Auth,
Storage и extensions. Обычная пустая PostgreSQL без Supabase-схем не подходит.
Отключить внешние SMTP, webhooks, cron, Edge/background workers и интеграции
на цели до импорта; не запускать restored production jobs. Не использовать
SSH-туннель или proxy на production под видом localhost.

Не копировать production JWT/API keys на цель. Не ослаблять RLS и не удалять
ошибочные строки/схемы только ради зелёного импорта. Несовместимую версию исправить
новой совместимой целью, сохранив исходный архив неизменным.

Ввести пароль **локальной** БД в `LINGOFLOW_RESTORE_PASSWORD` вне истории shell,
затем из корня репозитория выполнить:

```sh
node ops/backup-drill.mjs restore-local /private/tmp/lingoflow-db-drill --port 54322 --execute
unset LINGOFLOW_RESTORE_PASSWORD
```

Для официального self-hosted Docker-образа использовать административную роль:

```sh
node ops/backup-drill.mjs restore-local /private/tmp/lingoflow-db-drill --port 54322 --user supabase_admin --execute
unset LINGOFLOW_RESTORE_PASSWORD
```

Выполнить один подходящий вариант, пока цель пустая. Адрес и БД фиксированы:
`127.0.0.1`, `postgres`. Пользователь по умолчанию `postgres`; явно разрешён
только `supabase_admin`. Произвольные роли и connection parameters отвергаются.
Пароль не передаётся в argv. Унаследованные `PGHOSTADDR`, `PGSERVICE`, `PGOPTIONS`,
`.psqlrc` и `.pgpass` не управляют подключением. Перед импортом проверяются архив
и отсутствие public/private tables и Auth-пользователей. Непустая цель отвергается;
автоматического `DROP` или `--clean` нет. Подготовка defaults → roles → schema → data
идёт одной транзакцией с `ON_ERROR_STOP=1`; триггеры отключены только для data import согласно
официальному протоколу. Вывод SQL/ошибок subprocess не печатается.

Подготовка [default privileges](../ops/backup-restore-defaults.sql) возвращает
права создания объектов к стандартным PostgreSQL для импортёра и владельца
LingoFlow-объектов `postgres`. Это предотвращает наследование лишних grants
из self-hosted шаблона, включая identity sequences, создаваемые от имени владельца
таблицы. Права существующих managed-объектов и RLS не меняются. Затем dump
применяет собственные ACL и default privileges; ошибка откатывает всю транзакцию.

`local_import_completed` означает только нулевой exit code `psql`.
`acceptance_required: true` остаётся до отдельных проверок ниже. При ошибке
использовать новую disposable цель; не повторять импорт в частично изменённую БД.

## 3. Принять восстановление

1. Выполнить [агрегатные SQL-проверки](../ops/backup-restore-checks.sql) на источнике
   около capture и на цели. Сравнить Auth и 17 learner tables, RLS, policies,
   grants и extensions. Использовать одинаковый `search_path` при сравнении
   текстового представления policies; сортировать ACL entries, учитывать
   неявные стандартные права владельца. Сверить также права схем, функций,
   последовательностей и API-ролей. Разобрать расхождения; production writes после snapshot
   не объявлять потерей данных без выяснения времени. Одни row counts не доказывают
   идентичность данных.
2. На локальной копии проверить существующий QA-аккаунт, Today, историю B1,
   словарь и экспорт. Проверить RLS через anonymous, владельца и другого ученика.
   Не отправлять письма, не менять пароль реального пользователя.
3. Зафиксировать source commit, версии, private archive checksum, capture/import
   времена, длительность восстановления, результаты и отклонения. Не заявлять RPO,
   регулярный backup или полноценный DR только по одному импорту.
4. Удалить disposable цель и ненужные расшифрованные копии по согласованному сроку.
   Проверенную зашифрованную резервную копию хранить отдельно от ключа расшифровки.

SQL dump не включает Storage object bytes, Edge Functions, Vercel env/secrets,
SMTP/OAuth/redirect settings или DNS. Проверить эти компоненты отдельно;
миграции/код в Git и пустая копия пользовательского JSON-экспорта не заменяют dump.
Данные, хранящиеся только в браузере, включая локальные записи и черновики,
требуют отдельной процедуры.

Источники, проверенные 15 октября 2026:
[Supabase CLI backup/restore](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore),
[восстановление на self-hosted](https://supabase.com/docs/guides/self-hosting/restore-from-platform).

## Состояние · 18.10.2026

На текущей машине macOS 12.7.6 / Intel работают PostgreSQL-клиент 17.7,
Colima 0.10.3, Lima 2.2.0, QEMU 8.2.10, Docker CLI 29.9.1 и daemon 29.5.2.
Восстановление в изолированный self-hosted Supabase PostgreSQL 17 проверено.
Пароль источника в игнорируемом
`backend/.env.backup.local` проверен прямым read-only подключением, права 0600.
Повторный ввод или сброс пароля не требуется. Файл не загружается приложением
и не должен попадать в shell tracing, argv или отчёт.
Не выполнять shell source недоверенного файла.

Текущий checklist содержит 17 learner tables, включая агрегаты отдельного
письма B1. Старые отчёты о проверке 16 таблиц относятся к прежней схеме
и не считаются приёмкой нового backup. Capture и локальный restore приняты. [Внешняя копия принята 23 октября](backup-external-acceptance-2026-10-23.md):
Google Drive, ключ отдельно в Apple «Пароли», хранение 30 дней.
Регулярное создание свежих копий и автоматическое удаление ещё не настроены.

## Где взять пароль БД

Это пароль PostgreSQL проекта, заданный при создании Supabase-проекта,
а не пароль входа в LingoFlow, не пароль Dashboard и не API key. Он нужен
нативным PostgreSQL-инструментам для настоящего backup/restore.

1. Проверить сохранённый пароль проекта в своём менеджере паролей.
2. Открыть нужный проект в Supabase → **Database → Settings**. Если пароль
   утрачен, здесь есть **Reset database password**. Новый пароль потребует
   обновления существующих прямых PostgreSQL-подключений; сначала согласовать
   эту замену. Сброса пароля этим этапом не выполнялось.
3. Сохранить действующий пароль только локально в `backend/.env.backup.local`:
   `SUPABASE_DB_PASSWORD=...`, права файла `0600`. Значение не присылать в чат.

[Подключения, включая pg_dump](https://supabase.com/docs/guides/database/connecting-to-postgres),
[официальная инструкция сброса](https://supabase.com/docs/guides/troubleshooting/how-do-i-reset-my-supabase-database-password-oTs5sB).
