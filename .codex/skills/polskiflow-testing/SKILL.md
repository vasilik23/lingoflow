---
name: polskiflow-testing
description: Verify LingoFlow changes locally, in Supabase, and on Vercel. Use for Django tests, system and migration checks, regression coverage, browser testing, accessibility smoke checks, database assertions, RLS review, production smoke tests, and deployment log scans.
---

# LingoFlow testing

Run checks proportional to risk, with this full release baseline:

1. `backend/.venv/bin/python backend/manage.py test`
2. Django `check` and `makemigrations --check --dry-run`.
3. `git diff --check`; inspect migration and secret exposure.
4. For UI changes, start Django and use a real browser: meaningful content, key navigation, mobile viewport, no overlay, no console errors, and an annotated screenshot when useful.
   For progress changes, complete a real lesson from the current daily plan, then revisit the combined `Сегодня` screen. Assert that the completed lesson remains in the plan, its checkmark is visible, and both the completed count and percentage increase. Verify the persisted row when Supabase is in scope; a success screen alone is insufficient. Keep `/tasks/` covered only as a backward-compatible redirect to `/#daily-tasks`.
5. For Supabase changes, query prerequisites, apply only the reviewed ordered migration, assert row counts and behavior, then run security advisors. Confirm RLS and grants for every exposed table.
6. Wait for GitHub and Vercel checks. After merge, run only a concise production smoke test of the changed user flow and scan Vercel error logs. Do not repeat the full application test suite or broad browser regression in production unless the change is high-risk or the smoke test exposes a problem.
7. Report pass/fail, exact checks, deployment URL, and any known gap. Never describe an unrun check as passing.

Use temporary settings only outside the repository and never commit credentials or browser state.
