# LingoFlow API v1

Машиночитаемый OpenAPI 3.1 контракт доступен по
`GET /api/v1/openapi.json`. Он детерминирован, публично кэшируется и описывает
отдельные security boundaries для native Bearer API и браузерного cookie/CSRF
handoff. Документ не содержит credentials, пользовательские данные или ответы
учебных заданий.

Все ранние auth-отказы private v1 routes имеют тот же error envelope,
`401 authentication_required`, `Cache-Control: private, no-store` и
privacy-safe `X-Request-ID`. Публичные catalog, news и OpenAPI
сохраняют отдельную public cache-политику.

Bearer-only mutations use privacy-preserving per-user distributed rate limits.
An exceeded action budget returns `429 rate_limited`, `Retry-After`, private
no-store caching and performs no downstream write. Read-only contracts and
invalid/missing Bearer requests do not consume a mutation budget. The atomic
Supabase RPC stores counters in a non-exposed `private` schema, derives the
owner from `auth.uid()` and accepts neither a user ID nor client-selected quota.
An instance-local cache remains only as a best-effort availability fallback
when the limiter RPC itself is temporarily unreachable.

`GET/POST /api/v1/me/feedback/` extends the existing owner-scoped feedback
channel to separate clients. The server derives the owner from the Bearer
session, accepts only five known categories, a 20–2000 character message and an
optional internal path. Impact can be `normal`, `high`, or `blocking`; omitted
priority remains backward-compatible as `normal`. Client-provided user IDs and
external URLs are rejected; POST uses its own distributed mutation budget.

`GET /api/v1/catalog/` is the first read-only contract for future mobile and
other separate clients. `HEAD` is supported; mutation methods return `405`.
The endpoint is public because the same active learning tables are readable by
the Supabase `anon` role. It never includes profiles, progress, reviews,
personal dictionary entries, access tokens, quiz answers, flashcards, or full
lesson theory.

Authenticated separate clients load an active lesson from
`GET /api/v1/lessons/{lesson_id}/`. Flashcard content is returned directly;
choice and sentence-builder steps omit `correct` and `explanation`. A client
submits one bounded answer to `POST /api/v1/lessons/{lesson_id}/answer/`; only
then does the server return correctness and teaching feedback. Both endpoints
require an explicit Bearer token, accept no user ID and persist no answer.

`GET /api/v1/reading/` exposes the active learning-text library in bounded
pages with optional CEFR-level and text-query filters. Each item includes its
owner-scoped bookmark state. `GET /api/v1/reading/{text_id}/` returns paragraphs,
a normalized lemma-aware glossary, a conservative source/attribution card and
the linked comprehension lesson API path when available. News feeds remain
separate from stable learning content. Public `GET /api/v1/news/` returns only
bounded attributed headlines and validated HTTPS links from the same approved
feeds as the web News tab. It never proxies article bodies;
`meta.available=false` honestly represents an empty or temporarily unavailable
feed snapshot.

The native reading-to-dictionary flow posts only a surface form to
`POST /api/v1/reading/{text_id}/dictionary/`. The server resolves the canonical
lemma, translation and source context from that active text's glossary and
upserts it under the authenticated owner. Client-provided translations, lemmas,
context and user IDs are rejected. `DELETE /api/v1/me/dictionary/{word_id}/`
removes one owner-scoped entry; the existing personal-word RLS remains the final
authorization boundary.

## Envelope and versioning

Every response is JSON with these stable top-level fields:

```json
{
  "api_version": "v1",
  "meta": {
    "contract": "public-course-catalog",
    "contract_version": "1.0.0",
    "generated_at": "2026-09-02T10:00:00+00:00",
    "levels": ["A1", "A2", "B1", "B2", "C1", "C2"],
    "course_count": 6
  },
  "data": { "courses": [] }
}
```

`api_version` versions the URL family. `contract_version` follows semantic
versioning for this payload: additive optional fields increment the minor
version; removals, renames, type changes, or changed field meaning require a
new major API path. `generated_at` is an ISO 8601 UTC timestamp for the response
snapshot and must not be used as a content identifier.

## Catalog schema

- `course`: `id`, `title`, `description`, `level`, `position`, `topics`;
- `topic`: `id`, `title`, `description`, `emoji`, `position`, `lessons`;
- `lesson`: `id`, `title`, `description`, `kind`, `minutes`, `emoji`, `position`.

Only active courses, active topics with active lessons, and active lessons are
returned. Arrays are deterministic: courses, topics, and lessons are ordered by
`position`, then `id`. Clients should treat IDs as opaque strings and tolerate
new fields. Responses allow short shared-cache reuse; clients must not infer
that the catalog is permanently immutable.

## Learner contracts

`daily_goal_minutes` is the canonical saved budget in profile, bootstrap,
progress and Today responses. `daily_goal_lessons` remains deprecated for
older clients: 1–2 maps to 10 minutes, 3–4 to 15, and 5–10 to 30. New clients
should PATCH only `daily_goal_minutes`. A valid explicit Today `?minutes=`
overrides this request's plan without changing the saved goal. When both goal
fields are supplied, a single changed field wins; conflicting changes to both
are rejected with 400. Minute changes derive the compatibility count as 2/3/6.

The owner-scoped learner API provides the state needed by a separate client:

- `GET /api/v1/me/bootstrap/` — one cold-start snapshot with profile settings,
  aggregate progress, canonical daily plan, resume point and stable API links;
  failure of any required upstream returns `503`, never partial state;
- `GET /api/v1/me/achievements/` — seven deterministic milestones derived from
  current progress and dictionary state without duplicate mutable records;
- `GET /api/v1/me/progress/` — profile level and daily goal, streak, active
  days, deterministic completed lesson IDs, and week/month aggregates;
- `GET /api/v1/me/profile/` and strict `PATCH` — display name, curriculum
  target A1–C2 and `daily_goal_minutes` (10, 15 or 30). Partial updates merge with the
  current owner-scoped profile; user IDs and unknown fields are rejected;
- `DELETE /api/v1/me/account/` — permanently deletes only the authenticated
  caller after password reauthentication. The strict payload contains only
  `password`; ownership comes from the verified Bearer token. Wrong credentials
  return `403`, while worker outages return `503`;
- `GET /api/v1/me/export/` — complete schema-versioned portable snapshot of
  supported owner-scoped data. It shares the browser export source, paginates
  every dataset and returns `503` instead of a partial archive;
- `GET` and strict `PATCH /api/v1/me/reminder-preferences/` — owner-scoped
  opt-in, Warsaw time and complete disable control. The response explicitly
  reports `delivery_active=false` until a separately reviewed delivery channel
  exists;
- `GET /api/v1/me/today/` — canonical owner-scoped daily plan shared by
  separate clients: goal, ordered tasks, completion percentage and safe resume
  point. At most one task can have `plan_type=reinforcement` with a transparent
  `reinforcement_reason` (`cards_known`, `cards_total`, threshold), while the
  normal forward lesson remains first. A dictionary-review task links both the
  browser practice and native SM-2 queue;
- `GET /api/v1/me/sm2/` — personal dictionary review schedule, current due
  count, and the SM-2 fields required to render the learner's queue.
- `GET /api/v1/me/reading-bookmarks/` — deterministic IDs of saved texts.
- `GET /api/v1/me/history/?period=30&page=1` — owner-scoped завершения уроков
  страницами по 50 записей; доступны периоды 7/30/90 дней и всё время.
- `GET /api/v1/me/lesson-drafts/latest/` — последний незавершённый урок или
  `null`; временная ошибка Data API возвращает `503`, а не ложный пустой ответ.

Native clients add or remove a saved text with `PUT` or `DELETE` at
`/api/v1/me/reading-bookmarks/{text_id}/`. Mutations require an explicit Bearer
token, validate the active reading and never accept a user ID.

A native client schedules an owned dictionary card with
`POST /api/v1/me/sm2/{word_id}/review/` and one strict quality value:
`again`, `hard`, `good`, or `easy`. The server loads the current owner-scoped
state, calculates SM-2 and persists only scheduling fields. Client-supplied
ownership, intervals, repetitions, ease factors and dates are rejected.

Both accept the existing Supabase access token as
`Authorization: Bearer <access-token>`. Browser sessions may use the existing
HttpOnly cookie. Missing or invalid authentication returns `401`; mutations
return `405`; a temporary owner-scoped Data API failure returns `503` with
`error.code = "upstream_unavailable"` instead of an empty successful payload.

Learner responses use contract version `1.0.0`, `Cache-Control: private,
no-store`, and `Vary: Authorization, Cookie`. The backend forwards the same
user access token to Supabase, so existing RLS remains the authorization
boundary. The API never accepts a user ID from the client and never exposes
access or refresh tokens. Progress and SM-2 remain read-only; bookmark mutations
use idempotent set/delete semantics, while results use the event contract below.

History intentionally requires an explicit Bearer token even for GET and never
accepts a user ID. Invalid pagination returns `400`; a Data API failure returns
`503`, never a misleading empty successful page.

Native clients resume lessons through Bearer-only
`PUT /api/v1/me/lesson-drafts/{lesson_id}/` and clear a draft with idempotent
`DELETE` on the same path. PUT accepts exactly `step_index` and `score`; the
server derives the owner and lesson kind, verifies the active lesson and rejects
completed/out-of-range progress. Answers, exercise content, user IDs and tokens
are neither accepted in the payload nor returned.

## Lesson-result write contract

`POST /api/v1/me/lesson-results/` implements the first idempotent write
contract. Unlike read endpoints, it requires an explicit Supabase
`Authorization: Bearer` token; cookie-only requests are rejected even though
the view is CSRF-exempt for native clients. The JSON body is capped at 8 KiB
and follows [the result-sync design](api-result-sync.md).

The server rejects client-supplied ownership fields, validates the active
lesson and canonicalizes the payload before hashing it. The first event returns
`201 created`, an exact retry returns `200 duplicate`, and reuse of an
`event_id` for different data returns `409 idempotency_conflict`. Event storage
and the existing daily completion projection are updated atomically by a
`security invoker` Supabase function operating under the caller's RLS context.

Для Django/PWA-клиента доступен отдельный
`POST /api/v1/me/lesson-results/session/`. Он требует действующую HttpOnly
cookie-сессию и стандартный Django CSRF token, отвергает `Authorization` и не
возвращает bearer в браузер. Payload, идемпотентность, ответы и owner-scoped
Supabase RPC совпадают с основным write-контрактом.
