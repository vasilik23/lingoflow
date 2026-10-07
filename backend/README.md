# LingoFlow Python backend

Здесь находятся доменное ядро и основное production-приложение LingoFlow.
Сквозная проверка Django завершена, основной домен переключён, старый Next.js
deployment и legacy-код удалены. Следующий этап — системное наполнение контентом
с реестром источников и лицензий; подробный порядок описан в
`docs/python-migration.md`. Правила импорта находятся в
`docs/content-sources.md`, а последовательность тем A1–C1 — в
`docs/content-roadmap.md`.

Запуск тестов из корня репозитория:

```bash
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -v
```

Проверка Django после установки зависимостей:

```bash
cd backend
python manage.py check
python manage.py test
```

Проверенная версия зависимостей закреплена в `requirements.lock`.

## Supabase

Django-модели отображают существующие таблицы `public.profiles`,
`public.lesson_completions` и `public.flashcard_reviews` как `managed = False`:
Django не создаёт и не изменяет их своими миграциями. SQL сначала проверяется в
preview/staging-проекте Supabase и только после ручной проверки применяется к
production.

Для авторизации Django обращается к Supabase Auth. Настройте только публичные
параметры (service-role/secret key для этого не нужен):

```bash
export SUPABASE_URL=https://PROJECT.supabase.co
export SUPABASE_ANON_KEY=PUBLIC_ANON_KEY
```

Доступны браузерные маршруты `/login/`, `/register/`, `/logout/` и защищённая
страница `/`. Access и refresh tokens сохраняются в `HttpOnly`, `SameSite=Lax`
cookies; истёкший access token автоматически обновляется через Supabase Auth.
В production cookies помечаются `Secure`; локально это управляется переменной
`AUTH_COOKIE_SECURE`.

Главная страница читает профиль и историю `lesson_completions` через Supabase
Data API с access token пользователя. Она показывает настоящее имя, уровень,
текущую серию и выполненные сегодня уроки. Серия вычисляется по уникальным
UTC-датам завершений; при временной недоступности Data API интерфейс остаётся
рабочим и сообщает, что прогресс не загружен.

Минимальные production-переменные Django:

```bash
export DJANGO_DEBUG=false
export DJANGO_SECRET_KEY='long-random-production-secret'
export DJANGO_ALLOWED_HOSTS='your-domain.example'
export AUTH_COOKIE_SECURE=true
export DJANGO_SECURE_SSL_REDIRECT=true
```

HSTS намеренно не включается автоматически: после проверки HTTPS на настоящем
домене задайте `DJANGO_SECURE_HSTS_SECONDS` постепенно, затем при необходимости
включите `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` и `DJANGO_SECURE_HSTS_PRELOAD`.
Ошибочная HSTS-конфигурация долго кэшируется браузерами и трудно откатывается.

API-клиент также может передавать access token в `Authorization: Bearer …`.
Защищённый диагностический маршрут `GET /api/auth/me/` возвращает идентификатор
и email проверенного пользователя; отсутствие или отклонение токена даёт `401`.

## Templates + HTMX

Django уже воспроизводит главную страницу и маршруты `/lesson/words/`,
`/lesson/grammar/`, `/lesson/review/`, `/lesson/quiz/`. Переходы между
карточками и вопросами возвращают HTML-фрагменты через HTMX 2.0.10; формы
защищены CSRF. Без JavaScript остаются обычные серверные POST-ответы.

Интерфейс mobile-first использует собственную CSS-дизайн-систему из
`polskiflow/learning/static/polskiflow/app.css`: нижнюю навигацию на телефоне,
боковую навигацию на desktop, дневной progress-ring и единые компоненты уроков,
форм и обратной связи. Сборка не требует Node.js или CSS-препроцессора.

Учебный контент хранится в таблицах PostgreSQL `lessons`, `flashcards` и
`questions`. `polskiflow/content.py` читает только активные записи через Django
ORM, а `/admin/` позволяет управлять уроками, вопросами и карточками. Источником
DDL и начальных данных остаются `supabase/migrations/005_content_admin.sql` и
`006_revoke_profile_trigger_rpc.sql`. Database router не даёт Django повторно
создавать эти таблицы в PostgreSQL, но разрешает migrations создавать их в
локальной SQLite.

Контент организован иерархически: `Course → Topic → Lesson`. Тип урока хранится
в `Lesson.kind`, поэтому новые уроки могут использовать существующие механики
слов, грамматики и квизов без специальных slug в коде. Таблица
`lesson_flashcards` задаёт состав и порядок слов конкретного урока. Курсы, темы
и связи редактируются через Django Admin; браузерные роли Supabase могут читать
только активный опубликованный контент.

## Чтение и личный словарь

Маршрут `/reading/` открывает библиотеку коротких адаптированных текстов.
В читателе слова из авторского glossary выделены: по нажатию показывается
перевод, после чего слово можно добавить в `/dictionary/`. Тексты и словари
переводов редактируются через Django Admin в разделе `Reading texts`.

Публичный контент хранится в `reading_texts`, а пользовательские слова — в
`personal_words`. Django обращается к личному словарю через Supabase Data API с
access token пользователя. RLS разрешает каждому пользователю читать,
добавлять, изменять и удалять только собственные строки; `anon` не имеет доступа
к личным словам. Права Data API выданы явно и минимально.

Когда в словаре есть минимум четыре слова с разными переводами, маршрут
`/dictionary/practice/` создаёт мини-квиз: показывает польское слово и четыре
варианта перевода. Варианты и правильный ответ каждый раз восстанавливаются на
сервере из RLS-защищённых данных, поэтому скрытые поля браузера не считаются
доверенными. Итог сохраняется в дневной прогресс как `dictionary-practice`.

Завершение урока сохраняется в `lesson_completions` через Supabase Data API с
access token текущего пользователя. Upsert проходит через RLS и не использует
`service_role`.

Для прямого подключения ORM/Admin к PostgreSQL задайте стандартный URI:

```bash
export DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/postgres
python manage.py migrate
python manage.py createsuperuser
```

Без `DATABASE_URL` локальная разработка и тесты используют SQLite. Учётные
данные администратора Django отделены от пользовательской Supabase Auth.

Для Vercel используйте URI Supabase Transaction Pooler (порт `6543`). Django
отключает persistent connections и prepared statements, поскольку transaction
mode Supavisor предназначен для serverless, но не поддерживает prepared
statements. Для локальных migrations удобнее Direct или Session Pooler URI.

## CI и Vercel

GitHub Actions запускает тесты, system check и проверку миграций при каждом PR,
затрагивающем `backend/`. Vercel-проект `polskiflow-python` использует Root
Directory `backend`; платформа автоматически определяет Django по `manage.py`,
а основной production-адрес — `https://polish-learn.vercel.app`.

Обязательные переменные для Preview и Production перечислены в `.env.example`.
Секреты (`DJANGO_SECRET_KEY`, `DATABASE_URL`) задаются только в Vercel Dashboard. Привилегированное удаление аккаунта выполняет JWT-защищённая Supabase Edge Function; service-role credential не хранится в Vercel и не передаётся в HTML или клиентский JavaScript.
Production migrations уже применены, а служебные Django-таблицы защищены от
браузерных ролей миграцией `007_protect_django_internal_tables.sql`. Для нового
окружения перед первым входом в `/admin/` выполните Django migrations и создайте
отдельного superuser через доверенное окружение с тем же `DATABASE_URL`.
