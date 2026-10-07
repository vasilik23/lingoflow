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
prints the access token or response data.

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

The authenticated half remains an explicit release smoke until a dedicated
non-privileged account has automatic short-lived token rotation. Never turn a
static learner token into a long-lived GitHub secret merely to schedule it.
An external paging channel and an authenticated schedule remain launch gaps.
