---
name: polskiflow-content
description: Create, edit, and publish LingoFlow course content from A1 through C1. Use for complete topics containing vocabulary, grammar, flashcards, quizzes, readings, glossaries, source metadata, Django seeds, and Supabase data migrations.
---

# LingoFlow content

1. Read `docs/content-roadmap.md` and `docs/content-sources.md`; use `$polskiflow-material-research` for external foundations.
2. Build a vertical topic: 12–20 active units, two card sets, concise grammar, at least five explained exercises, a reading appropriate to the level, glossary, and eight-question final quiz.
3. Use natural Polish, contextual Russian translations, one unambiguous answer per question, and explanations that teach the rule.
4. Keep at least 90% of an A-level reading known or inferable. Increase genre, register, argumentation, and mediation demands progressively through C1.
5. Mark original work with `origin`, `created_for`, and `verified_at`; store full attribution for external work.
6. Seed SQLite through an ordered Django migration and production through a matching Supabase migration. Make rerunnable inserts explicit with `on conflict` where safe.
7. Add count, metadata, ordering, glossary, and route tests. Then use `$polskiflow-testing` and `$polskiflow-git`.

Do not claim official CEFR certification; levels are curriculum targets until independently validated.
