# Production operations baseline

LingoFlow provides two unauthenticated, privacy-safe probes:

- `GET /health/` is a liveness check. It only confirms that Django can respond and
  never calls the database or Supabase Auth.
- `GET /ready/` checks the default database with `SELECT 1`. On Vercel it also
  confirms that the required Supabase variables are present. It returns HTTP 503
  when the application should not receive traffic.

Both responses use `Cache-Control: no-store` and expose only component states,
never exception messages, connection strings, keys, versions, or user data.

Every response receives an `X-Request-ID`. HTTP 5xx responses, uncaught
exceptions, and slow requests are written to the platform log as structured
`key=value` events. Logs contain method, path without query parameters, status,
duration, and request ID; they do not contain bodies, cookies, email addresses,
tokens, IP addresses, or exception messages. Exception logs expose only the
exception class. `REQUEST_SLOW_THRESHOLD_MS` defaults to 1500 ms.

Minimal production checks:

```shell
curl --fail --max-time 10 https://lingoflow-learn.vercel.app/health/
curl --fail --max-time 10 https://lingoflow-learn.vercel.app/ready/
```

Use the returned `X-Request-ID` to correlate a failed client request with Vercel
runtime logs. These probes do not replace synthetic user-flow monitoring,
database backups, or alerts.

## Read-only synthetic release smoke

The `production_smoke` management command verifies the public probes, OpenAPI,
catalog, authenticated bootstrap and complete data-export contracts. It only
uses `GET`, checks request IDs and the private/no-store boundary, and never
prints the access token or response data. Each response is limited to 2 MiB;
malformed nested contracts, invalid UTF-8 and interrupted bodies fail with a
sanitized error. Non-200 bodies are not read. Private cache directives must
match exactly; request IDs may contain only ASCII letters, digits, hyphens
and underscores, up to 128 characters. Larger exports fail this synthetic
probe; use a small dedicated account rather than treating it as an export tool.

Use a short-lived token belonging to a dedicated non-privileged smoke account:

```shell
export POLSKIFLOW_SMOKE_ACCESS_TOKEN='short-lived-token'
backend/.venv/bin/python backend/manage.py production_smoke \
  https://lingoflow-learn.vercel.app
```

The token is accepted only through an environment variable, not a CLI argument.
Do not store it in Git, workflow logs or long-lived repository variables.

Alternatively, put the short-lived token in the ignored local file
`backend/.env.smoke.local` with owner-only permissions (`chmod 600`). Keep its
only assignment as `POLSKIFLOW_SMOKE_ACCESS_TOKEN=...`; never paste it into chat.
The command does not automatically load this file. From the repository root:

```shell
set +x
set -a
. backend/.env.smoke.local
set +a
backend/.venv/bin/python backend/manage.py production_smoke \
  https://lingoflow-learn.vercel.app
unset POLSKIFLOW_SMOKE_ACCESS_TOKEN
```

Use only a local file you control; shell sourcing executes its contents. An
empty or expired token does not count as a successful authenticated smoke.

The public half runs automatically every four hours from
`.github/workflows/production-smoke.yml`. It sends no credentials and checks
health, readiness, OpenAPI and catalog. A failure marks the workflow red and
uses normal GitHub Actions notifications as the initial alert channel.

The authenticated half uses the fresh-session schedule described below.
It was enabled on 16 October 2026 with a separate permanent monitoring account;
the first manual GitHub run passed both jobs. Actual scheduled execution was
confirmed on 17 October; see the receipt below. Alert recipient delivery and
external paging remain launch gaps.

## Authenticated schedule (enabled)

`production_smoke --fresh-session https://lingoflow-learn.vercel.app` obtains a
new short-lived password-grant session for each run. Credentials are read from
environment variables; access/refresh tokens are not written to files, workflow
outputs, artifacts or GitHub Secrets. The refresh token is never reused.
The existing API probes remain GET-only. Login and local logout are Auth POSTs;
this mode therefore creates and revokes an Auth session, but does not alter
learning data. There is no automatic signup, email, retry or public-only fallback.

Activation steps for the operator:

1. Prepare a dedicated confirmed, non-anonymous learner with no admin privileges
   and no real learner data. Verify its UUID and ownership in Supabase. Do not use
   a personal account or the temporary QA mailbox. Use an operator-controlled
   permanent email so password recovery remains possible. This command checks
   UUID, non-anonymous status, `authenticated` role and a nonempty Auth email
   confirmation field; custom app grants still require operator verification.
2. Set access-token expiry to no more than 3600 seconds in the Auth project;
   the command accepts a reported lifetime of 300–3600 seconds. Local signout
   revokes this session's refresh ability; issued access tokens can remain valid
   until their expiry. A terminated runner may miss cleanup.
3. Create GitHub environment `production-smoke`, restrict it to `main`, and store
   these environment Secrets through GitHub's secret UI (never PR text or logs):
   `LINGOFLOW_SMOKE_AUTH_URL` (hosted `https://<20-character-ref>.supabase.co`),
   `LINGOFLOW_SMOKE_PUBLISHABLE_KEY` (publishable `sb_publishable_` key),
   `LINGOFLOW_SMOKE_EMAIL`, `LINGOFLOW_SMOKE_PASSWORD`, `LINGOFLOW_SMOKE_USER_ID`.
   Legacy anon/service-role keys are deliberately not accepted in this mode.
4. Set repository variable `LINGOFLOW_AUTHENTICATED_SMOKE_ENABLED=true` only after
   the environment is ready. Run Production Smoke manually on `main`; require
   all eight probes and session cleanup to pass. If environment approvals are
   required, scheduled runs will wait for them; configure protection accordingly.
5. Check the next scheduled run (every four hours). Enable GitHub Actions failure
   notifications for the responsible operator. This is the existing initial
   channel; external paging and a verified recipient remain separate work.
6. Rotate the dedicated account password in Supabase and replace its environment
   secret; rerun the workflow. Never maintain a static access/refresh token in
   GitHub. To disable the job, remove/set the repository variable to `false`.

The job is skipped while its enable variable is absent. Missing credentials,
wrong UUID, failed login, malformed response, excessive token lifetime, failed
probe or failed logout make an enabled job red. It sends credentials only to
validated hosted Supabase Auth, rejects redirects, uses a bounded response and
never prints Auth bodies. A manual fresh-session production run on the temporary
QA account passed on 14 October 2026; this does not activate the schedule or
replace the permanent dedicated account required above.

### Configuration status — 16 October 2026

The GitHub environment `production-smoke` now exists with custom deployment
branch policies allowing exactly branch `main` (no tag policy). The authenticated
job also checks `github.ref == 'refs/heads/main'`; both checkout steps disable
persisted Git credentials. The environment restriction is the secret boundary;
the workflow condition is an additional guard.

The operator supplied a permanent email. Its existing account was left intact;
a separate Gmail plus-alias account was created through normal registration and
onboarding. It has the ordinary `authenticated` role, confirmed Auth email,
no custom privileges and a minimal A1 profile. Five environment secrets are set,
and `LINGOFLOW_AUTHENTICATED_SMOKE_ENABLED=true`. The random password remains
only in the ignored owner-only local credentials file and GitHub environment.
No email or password is published in this runbook.

Correction to the earlier setup note: registration redirects to `/welcome/`,
not `/onboarding/`. The setup harness misread successful signup as failure;
the later HTTP 422 meant “already registered”, not rejection of the reserved
address. The unused reserved-address account was identified by exact UUID and
creation timestamp, checked for empty learning data and deleted; its sessions
were also removed. The permanent account was finished using `/welcome/`.
Auth auto-confirm was already enabled and was not changed.

The stricter session validator passed all six production probes on the existing
QA account on 16 October, including local logout. This was a one-off verification,
not activation of the schedule. Release baseline: 1067 Django tests, system check,
migration drift and diff check passed.

The permanent account then passed the same six probes locally and in
[GitHub run 38881443022](https://github.com/vasilik23/lingoflow/actions/runs/38881443022):
`public-contracts` passed four checks and `authenticated-contracts` passed six,
including normal local logout. Residual registration setup sessions were
separately revoked. No learning completions or personal words were created.
This proves manual execution with the configured secrets, not delivery of a
future cron event or external alert. [Activation receipt](monitoring-activation-2026-10-16.md).

References: [GitHub environments](https://docs.github.com/en/rest/deployments/environments),
[deployment branch policies](https://docs.github.com/en/rest/deployments/branch-policies).

Protocol reference: [official Supabase Auth OpenAPI](https://github.com/supabase/auth/blob/master/openapi.yaml)
(password grant and `logout?scope=local`).

## Backup and restore drill

[Operator runbook](backup-restore-drill.md) covers three CLI dumps, private
archives, checksums and guarded import into an empty local Supabase. The Node
tool and its boundary tests are prepared; no database dump or real restore has
been performed. Docker, psql and operator database access are still required.
The actual restore, RLS/data acceptance and separate encrypted copy remain
launch work. User JSON export is not a project database backup.

### Scheduled execution confirmed — 17 October 2026

The first post-activation scheduled run on 16 October passed both jobs and all six
then-existing probes; five scheduled runs through 17 October are confirmed successful.
[Evidence and coverage extension](monitoring-scheduled-2026-10-17.md). Current full smoke
also checks practice/reminder preferences (eight probes total), including strict types
and private/no-store headers. This does not prove alert recipient delivery, background
reminders, two-user RLS isolation or database restore.

### Alert delivery acceptance · 18 October 2026

A separate, manual [Alert Delivery Test](alert-delivery-test.md) is prepared.
It can generate one intentional failed workflow only after explicit operator
authorization, on `main`, with `SEND_TEST_ALERT`; it does not access production
or secrets. Its failure status alone does not prove notification delivery.
The operator must confirm receipt/channel/time; external paging is separate.
No test dispatch or receipt is claimed by this preparation.
