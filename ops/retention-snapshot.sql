-- Run as the database operator, not through an ordinary learner token.
-- Caller must keep the returned UUID inventory in a private encrypted directory.
-- The function is SECURITY INVOKER, SELECT-only, and not exposed in public REST.
select private.retention_review_snapshot() as retention_snapshot;
