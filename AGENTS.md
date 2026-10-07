# LingoFlow development rules

- The production application is Python/Django in `backend/`.
- Keep secrets out of Git; use local environment files and Vercel environment variables.
- Run Django tests, system checks, and the migration drift check before publishing changes.
- Treat `supabase/migrations/` as ordered production database changes; review RLS and grants for every new user-facing table.
