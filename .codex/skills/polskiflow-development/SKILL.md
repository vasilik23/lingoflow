---
name: polskiflow-development
description: Implement and review LingoFlow frontend and backend changes in the Python/Django application. Use for Django models, views, templates, HTMX, CSS, routing, admin, Supabase-backed repositories, UI modernization, accessibility, and application architecture.
---

# LingoFlow development

1. Read `AGENTS.md`, relevant models, views, templates, tests, and migrations before editing.
2. Treat `backend/` as the production application. Do not revive removed legacy frontend code.
3. Keep domain logic in Python modules, persistence behind focused repository/store functions, and templates free of business logic.
4. Prefer server-rendered Django Templates and HTMX. Preserve keyboard access, semantic HTML, mobile layout, and visible focus states.
5. For model changes, create a Django migration and a matching ordered Supabase migration. Review existing RLS and grants.
6. Keep secrets in local environment files and Vercel variables only.
7. Make a small coherent change, add regression tests, and hand off to `$polskiflow-testing`.

For user-visible UI changes, verify the actual page in a browser at mobile and desktop widths.
