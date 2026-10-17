# Scheduled production monitoring — 17 October 2026

## Confirmed execution

The first observed scheduled run after dedicated-account activation is
[38906550039](https://github.com/vasilik23/lingoflow/actions/runs/38906550039),
created **16 October 2026, 13:16:07 UTC**, source
`866506d9c341a14b79100322088f3b91c80f05a2`.
Both `public-contracts` and `authenticated-contracts` completed successfully;
the fresh-session step ran rather than being skipped. It checked the six
then-existing endpoints and required local Auth logout before success.

Further scheduled runs passed:

| Created UTC | Run |
| --- | --- |
| 16 Oct 19:33:45 | [38955825369](https://github.com/vasilik23/lingoflow/actions/runs/38955825369) |
| 16 Oct 22:51:40 | [38978221162](https://github.com/vasilik23/lingoflow/actions/runs/38978221162) |
| 17 Oct 04:28:38 | [39002705520](https://github.com/vasilik23/lingoflow/actions/runs/39002705520) |
| 17 Oct 12:11:56 | [39031579583](https://github.com/vasilik23/lingoflow/actions/runs/39031579583) |

The latest run's public and authenticated job/step conclusions were also checked
individually. These timestamps are actual starts, not guarantees that GitHub
runs exactly at the cron minute or every four wall-clock hours. No fixed-time
SLA is claimed.

## Coverage extension

Full smoke now adds GET `/api/v1/me/practice-preferences/` and
`/api/v1/me/reminder-preferences/` after bootstrap/export: **eight checks** total;
public-only remains four. Existing schedule, environment secrets, branch guard
and ordinary monitor identity remain unchanged. Both jobs use Ubuntu 24.04,
aligned with the project's Python CI, rather than a moving `ubuntu-latest`.

The new checks validate contract envelopes, boolean preference flags, the
configured marker, valid HH:MM and Europe/Warsaw, and the boolean delivery flag.
They accept both enabled and disabled preferences without changing either.
Private/no-store, bounded JSON, no redirects and sanitized request IDs apply
as before. Failures do not print response bodies, settings or credentials.

This is an authenticated read-only availability/schema check. It does not
exercise PATCH, confirm opt-in delivery, validate personalized recommendation
quality, prove two-user RLS isolation or mutate learning results. Earlier
scheduled runs had six probes; they do not retroactively prove the two new ones.
The next normal workflow run validates the expanded coverage separately.

## Still open

- Confirm that an operator receives a genuine failure notification and establish
  the external alert channel. Successful scheduled runs do not prove delivery.
  No deliberate production outage or external message was created for this check.
- Perform a real backup/restore and data/RLS acceptance. This machine still lacks
  Docker and psql; no database dump or restore occurred.
- Complete the separate human/legal/content acceptance steps in README.

## Local operator verification of extended coverage

On 17 October the updated command ran against canonical production with the
existing dedicated monitoring account: all eight probes passed and the fresh
session exited through normal local logout. Credentials were loaded from the
ignored owner-only operator file into process environment, never command arguments.
No preferences, learning results or words were written. This verifies the updated
local command against production, not yet the updated GitHub runner.

Release checks: 1087 Django tests, system check, migration drift and diff check
passed. No database schema, RLS/grants, application UI or runtime route changes.
