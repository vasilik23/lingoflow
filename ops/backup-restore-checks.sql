-- Read-only aggregate checks: run on the source near capture and on the local restore.
-- Keep output private. Concurrent production writes may explain count differences.
SELECT 'auth.users' AS dataset, count(*) AS rows FROM auth.users
UNION ALL SELECT 'profiles', count(*) FROM public.profiles
UNION ALL SELECT 'lesson_completions', count(*) FROM public.lesson_completions
UNION ALL SELECT 'lesson_result_events', count(*) FROM public.lesson_result_events
UNION ALL SELECT 'lesson_drafts', count(*) FROM public.lesson_drafts
UNION ALL SELECT 'personal_words', count(*) FROM public.personal_words
UNION ALL SELECT 'reading_bookmarks', count(*) FROM public.reading_bookmarks
UNION ALL SELECT 'lesson_bookmarks', count(*) FROM public.lesson_bookmarks
UNION ALL SELECT 'learner_mistakes', count(*) FROM public.learner_mistakes
UNION ALL SELECT 'lesson_notes', count(*) FROM public.lesson_notes
UNION ALL SELECT 'learning_collections', count(*) FROM public.learning_collections
UNION ALL SELECT 'learning_collection_items', count(*) FROM public.learning_collection_items
UNION ALL SELECT 'user_feedback', count(*) FROM public.user_feedback
UNION ALL SELECT 'reminder_preferences', count(*) FROM public.reminder_preferences
UNION ALL SELECT 'b1_mock_attempts', count(*) FROM public.b1_mock_attempts
UNION ALL SELECT 'b1_section_attempts', count(*) FROM public.b1_section_attempts
UNION ALL SELECT 'b1_writing_attempts', count(*) FROM public.b1_writing_attempts
UNION ALL SELECT 'b1_run_attempts', count(*) FROM public.b1_run_attempts
ORDER BY dataset;

-- Review security definitions, not only learner row counts.
SELECT n.nspname AS schema, c.relname AS table_name,
       c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS rls_forced,
       c.relacl::text AS grants
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN ('public', 'private') AND c.relkind IN ('r', 'p')
ORDER BY 1, 2;

SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies WHERE schemaname IN ('public', 'private')
ORDER BY schemaname, tablename, policyname;

SELECT extname, extversion FROM pg_extension ORDER BY extname;
