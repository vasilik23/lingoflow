# Performance baseline

Дата первого замера: 31 августа 2026. Production:
`https://lingoflow-learn.vercel.app`.

## Цели

Для field-данных на 75-м перцентиле:

- LCP ≤ 2,5 с;
- INP ≤ 200 мс;
- CLS ≤ 0,1.

Пока трафика недостаточно для надёжного field-среза, релизный lab baseline
измеряется Lighthouse в мобильном режиме. Lighthouse не измеряет INP без
реального ввода, поэтому в lab используется TBT как диагностический proxy, а
INP должен быть добавлен из real-user monitoring после накопления данных.

Рабочий lab budget для ключевых маршрутов:

- performance score ≥ 90;
- accessibility score ≥ 95;
- LCP ≤ 2,5 с;
- CLS ≤ 0,1;
- TBT ≤ 200 мс;
- TTFB фиксируется для диагностики, но один холодный serverless-запуск не
  считается регрессией без повторных замеров.

## Первый production-замер

Команда запускается по три раза для каждого маршрута; в таблицу попадает
медиана. Первый диагностический прогон до оптимизации внешнего шрифта:

| Маршрут | Score | LCP | CLS | TBT | TTFB |
| --- | ---: | ---: | ---: | ---: | ---: |
| `/login/` | 61 | 5,53 с | 0,014 | 0 мс | 106 мс |
| `/sources/` | 91 | 2,83 с | 0,016 | 0 мс | 41 мс |

Lighthouse показал до 3,86 с потенциальной экономии на render-blocking
Google Fonts. Поэтому внешний Manrope удалён из критического пути в пользу
нативного системного стека.

Production-медиана трёх последовательных прогонов после деплоя `ad5d15c`:

| Маршрут | Score | LCP | CLS | TBT | TTFB |
| --- | ---: | ---: | ---: | ---: | ---: |
| `/login/` | 99 | 1,89 с | 0 | 51 мс | 41 мс |
| `/sources/` | 99 | 1,83 с | 0 | 32 мс | 41 мс |

Параллельные прогоны не используются: конкуренция нескольких экземпляров
Chrome за CPU искусственно увеличивает TBT. Каждый маршрут измеряется строго
последовательно.

## Воспроизводимый запуск

```bash
npx --yes lighthouse https://lingoflow-learn.vercel.app/login/ \
  --only-categories=performance \
  --form-factor=mobile \
  --screenEmulation.mobile=true \
  --throttling-method=simulate \
  --output=json \
  --output-path=/tmp/polskiflow-login-lh.json \
  --chrome-flags='--headless --no-sandbox' \
  --quiet
```

Повторить для `/sources/` и минимум одного авторизованного ключевого маршрута.
Для авторизованной страницы использовать временный Chrome-профиль тестового
аккаунта вне репозитория; cookies, токены и credentials не сохранять в Git.

Перед сравнением результатов фиксировать дату, deployment commit, viewport,
режим throttling и медиану не менее трёх прогонов. Lab-данные не выдавать за
field Core Web Vitals.

Три последовательных JSON-отчёта проверяются одной воспроизводимой командой:

```bash
cd backend
.venv/bin/python manage.py check_lighthouse_budget \
  /tmp/run-1.json /tmp/run-2.json /tmp/run-3.json
```

Команда вычисляет медианы performance/accessibility score, LCP, CLS, TBT и
диагностического TTFB и возвращает ненулевой код при нарушении release budgets. Её можно использовать
в CI после отдельного последовательного шага сбора Lighthouse-артефактов;
INP остаётся field-метрикой и этим lab-check не подменяется.

Ручной GitHub Actions workflow `Lighthouse Preview` принимает публичный HTTPS
URL конкретного Vercel Preview, последовательно делает по три мобильных прогона
performance и accessibility для `/login/` и `/sources/`, проверяет обе медианы и сохраняет JSON-артефакты на
14 дней. Он не принимает cookies или credentials, поэтому авторизованные
маршруты остаются отдельной ручной проверкой с временным профилем вне Git.

Источники методики:

- [Web Vitals](https://web.dev/articles/vitals)
- [Lighthouse performance scoring](https://developer.chrome.com/docs/lighthouse/performance/performance-scoring)
