---
name: polskiflow-git
description: Run the LingoFlow Git and GitHub delivery workflow. Use for branches, commits, pull requests, CI checks, merges, repository cleanup, release coordination, and synchronizing Supabase migrations with Vercel deployments.
---

# LingoFlow Git workflow

1. Start from a clean, current `main`; preserve unrelated user changes.
2. Create one `agent/<purpose>` branch per coherent change.
3. Inspect `git status`, `git diff`, `git diff --check`, and staged files. Never commit secrets, local databases, environments, or generated caches.
4. Run `$polskiflow-testing` before publication.
5. Use an imperative commit subject and a PR body covering outcome, tests, database impact, and deployment ordering.
6. Wait for GitHub CI and Vercel Preview. For database-dependent code, use the safe two-phase order: compatible migration, verification, then merge/deploy.
7. Merge only when authorized, sync local `main`, wait for production, run smoke tests, and scan error logs.

Never rewrite shared history or use destructive Git commands unless the user explicitly requests and approves the exact target.
