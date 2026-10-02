alter table public.b1_mock_attempts
  add column if not exists attempt_id uuid not null default gen_random_uuid();

create unique index if not exists b1_mock_attempts_user_attempt_key
  on public.b1_mock_attempts (user_id, attempt_id);

comment on column public.b1_mock_attempts.attempt_id is
  'Opaque server-signed idempotency key. Replayed form submissions keep the first aggregate result.';
