"""Static, deterministic API v1 description for separate clients."""


def build_openapi_v1():
    error_response = {
        "description": "Request failed",
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ErrorEnvelope"}}
        },
    }
    private_errors = {str(code): error_response for code in (401, 405, 503)}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "LingoFlow API",
            "version": "1.0.0",
            "description": (
                "Versioned contracts for the LingoFlow curriculum and learner-owned state. "
                "Curriculum levels are targets, not official CEFR certification."
            ),
        },
        "servers": [{"url": "/", "description": "Same-origin deployment"}],
        "paths": {
            "/api/v1/me/account/": {
                "delete": {
                    "operationId": "deleteLearnerAccount",
                    "summary": "Permanently delete the authenticated account after password reauthentication",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AccountDeletionRequest"}}}},
                    "responses": {"200": _json_response("Account deleted"), **{str(code): error_response for code in (400, 401, 403, 405, 413, 415, 429, 503)}},
                }
            },
            "/api/v1/me/export/": {
                "get": {
                    "operationId": "exportLearnerData",
                    "summary": "Export all supported owner-scoped learner data",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Complete portable learner snapshot"), **private_errors},
                }
            },
            "/api/v1/me/reminder-preferences/": {
                "get": {
                    "operationId": "getLearnerReminderPreferences",
                    "summary": "Get explicit opt-in reminder settings and delivery status",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Owner-scoped reminder preferences"), **private_errors},
                },
                "patch": {
                    "operationId": "patchLearnerReminderPreferences",
                    "summary": "Enable, configure, or disable reminder preferences",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ReminderPreferencesPatchRequest"}}}},
                    "responses": {"200": _json_response("Updated reminder preferences"), **{str(code): error_response for code in (400, 401, 413, 415, 429, 503)}},
                },
            },
            "/api/v1/catalog/": {
                "get": {
                    "operationId": "getCatalog",
                    "summary": "Get the public active course catalog",
                    "responses": {"200": _json_response("Public course catalog")},
                }
            },
            "/api/v1/news/": {
                "get": {
                    "operationId": "getNewsHeadlines",
                    "summary": "Get bounded attributed headlines from approved Polish feeds",
                    "parameters": [
                        {"name": "category", "in": "query", "schema": {"type": "string", "enum": ["politics", "sport", "culture", "economy"]}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 12, "default": 12}},
                    ],
                    "responses": {"200": _json_response("Public attributed headline snapshot"), "400": error_response},
                }
            },
            "/api/v1/lessons/{lesson_id}/": {
                "parameters": [{"name": "lesson_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 100}}],
                "get": {
                    "operationId": "getNativeLesson",
                    "summary": "Get active lesson steps without answer keys",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Lesson content without answer keys"), **{str(code): error_response for code in (401, 404, 503)}},
                },
            },
            "/api/v1/lessons/{lesson_id}/answer/": {
                "parameters": [{"name": "lesson_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 100}}],
                "post": {
                    "operationId": "evaluateNativeLessonAnswer",
                    "summary": "Evaluate one choice or sentence-builder answer server-side",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LessonAnswerRequest"}}}},
                    "responses": {"200": _json_response("Answer feedback"), **{str(code): error_response for code in (400, 401, 404, 413, 415, 429)}},
                },
            },
            "/api/v1/listening/": {
                "get": {
                    "operationId": "getNativeListeningExercises",
                    "summary": "Get listening transcripts, fragments, and questions without answer keys",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Listening exercises without answer keys"), **{str(code): error_response for code in (401, 503)}},
                }
            },
            "/api/v1/listening/{exercise_id}/answer/": {
                "parameters": [{"name": "exercise_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 100}}],
                "post": {
                    "operationId": "evaluateNativeListeningAnswer",
                    "summary": "Evaluate one listening choice without persistence",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ListeningAnswerRequest"}}}},
                    "responses": {"200": _json_response("Listening answer feedback"), **{str(code): error_response for code in (400, 401, 404, 413, 415, 429)}},
                },
            },
            "/api/v1/interaction/": {
                "get": {
                    "operationId": "getNativeInteractionScenarios",
                    "summary": "Get interaction and mediation prompts without answer keys",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Interaction scenarios without answer keys"), **{str(code): error_response for code in (401, 503)}},
                }
            },
            "/api/v1/interaction/{scenario_id}/answer/": {
                "parameters": [{"name": "scenario_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 100}}],
                "post": {
                    "operationId": "evaluateNativeInteractionAnswer",
                    "summary": "Evaluate one interaction choice or sequence without persistence",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/InteractionAnswerRequest"}}}},
                    "responses": {"200": _json_response("Interaction answer feedback"), **{str(code): error_response for code in (400, 401, 404, 413, 415, 429)}},
                },
            },
            "/api/v1/diagnostic/": {
                "get": {
                    "operationId": "getNativeDiagnostic",
                    "summary": "Get a preliminary diagnostic without answer keys",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Diagnostic form without answer keys"), **{str(code): error_response for code in (401, 503)}},
                }
            },
            "/api/v1/diagnostic/evaluate/": {
                "post": {
                    "operationId": "evaluateNativeDiagnostic",
                    "summary": "Evaluate a complete diagnostic without persistence",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DiagnosticRequest"}}}},
                    "responses": {"200": _json_response("Preliminary recommendation and feedback"), **{str(code): error_response for code in (400, 401, 413, 415, 429)}},
                }
            },
            "/api/v1/writing/": {
                "get": {
                    "operationId": "getNativeWritingPrompts",
                    "summary": "Get B1/B2 writing prompts and structural criteria",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Writing prompts and honest criteria"), **{str(code): error_response for code in (401, 503)}},
                }
            },
            "/api/v1/writing/{prompt_id}/check/": {
                "parameters": [{"name": "prompt_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 100}}],
                "post": {
                    "operationId": "checkNativeWritingDraft",
                    "summary": "Check observable draft structure without persistence or language grading",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/WritingCheckRequest"}}}},
                    "responses": {"200": _json_response("Observable structural checks"), **{str(code): error_response for code in (400, 401, 404, 413, 415, 429)}},
                },
            },
            "/api/v1/reading/": {
                "get": {
                    "operationId": "getNativeReadingLibrary",
                    "summary": "Get a filtered page of active learning texts",
                    "security": [{"supabaseBearer": []}],
                    "parameters": [
                        {"name": "level", "in": "query", "schema": {"type": "string", "enum": ["A1", "A2", "B1", "B2", "C1", "C2"]}},
                        {"name": "q", "in": "query", "schema": {"type": "string", "maxLength": 120}},
                        {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 1}},
                    ],
                    "responses": {"200": _json_response("Owner-aware reading library page"), **{str(code): error_response for code in (400, 401, 503)}},
                }
            },
            "/api/v1/reading/{text_id}/": {
                "parameters": [{"name": "text_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 80}}],
                "get": {
                    "operationId": "getNativeReadingText",
                    "summary": "Get paragraphs, lemma glossary, source metadata, and comprehension link",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Active reading text detail"), **{str(code): error_response for code in (401, 404, 503)}},
                },
            },
            "/api/v1/reading/{text_id}/dictionary/": {
                "parameters": [{"name": "text_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 80}}],
                "post": {
                    "operationId": "saveReadingGlossaryWord",
                    "summary": "Save a server-verified glossary lemma to the learner dictionary",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/GlossaryWordRequest"}}}},
                    "responses": {"200": _json_response("Canonical lemma saved"), **{str(code): error_response for code in (400, 401, 404, 413, 415, 429, 503)}},
                },
            },
            "/api/v1/me/progress/": {
                "get": {
                    "operationId": "getLearnerProgress",
                    "summary": "Get aggregate progress for the authenticated learner",
                    "security": [{"supabaseBearer": []}, {"browserSession": []}],
                    "responses": {"200": _json_response("Owner-scoped progress"), **private_errors},
                }
            },
            "/api/v1/me/profile/": {
                "get": {
                    "operationId": "getLearnerProfile",
                    "summary": "Get bounded owner-scoped profile settings",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Profile settings"), **private_errors},
                },
                "patch": {
                    "operationId": "patchLearnerProfile",
                    "summary": "Update display name, curriculum level, or daily goal",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProfilePatchRequest"}}}},
                    "responses": {"200": _json_response("Updated profile settings"), **{str(code): error_response for code in (400, 401, 413, 415, 429, 503)}},
                },
            },
            "/api/v1/me/feedback/": {
                "get": {
                    "operationId": "getLearnerFeedback",
                    "summary": "List owner-scoped feedback and statuses",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Owner-scoped feedback history"), **private_errors},
                },
                "post": {
                    "operationId": "createLearnerFeedback",
                    "summary": "Create one owner-scoped feedback report",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/FeedbackRequest"}}}},
                    "responses": {"201": _json_response("Feedback accepted"), **{str(code): error_response for code in (400, 401, 413, 415, 429, 503)}},
                },
            },
            "/api/v1/me/today/": {
                "get": {
                    "operationId": "getLearnerToday",
                    "summary": "Get the authenticated learner's canonical daily plan",
                    "security": [{"supabaseBearer": []}],
                    "parameters": [{"name": "minutes", "in": "query", "required": False, "schema": {"type": "integer", "enum": [10, 15, 30], "default": 15}}],
                    "responses": {"200": _json_response("Owner-scoped daily goal, tasks, progress, and resume point"), **private_errors},
                }
            },
            "/api/v1/me/bootstrap/": {
                "get": {
                    "operationId": "getLearnerBootstrap",
                    "summary": "Get profile, progress, daily plan, resume point, and API links in one snapshot",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Owner-scoped native client bootstrap snapshot"), **private_errors},
                }
            },
            "/api/v1/me/achievements/": {
                "get": {
                    "operationId": "getLearnerAchievements",
                    "summary": "Get deterministic achievement progress derived from owner-scoped state",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Owner-scoped achievement progress"), **private_errors},
                }
            },
            "/api/v1/me/history/": {
                "get": {
                    "operationId": "getLearnerHistory",
                    "summary": "Get a paginated owner-scoped lesson completion history",
                    "security": [{"supabaseBearer": []}],
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 500, "default": 1}},
                        {"name": "period", "in": "query", "schema": {"type": "string", "enum": ["7", "30", "90", "all"], "default": "30"}},
                    ],
                    "responses": {"200": _json_response("Owner-scoped lesson history"), **{str(code): error_response for code in (400, 401, 405, 503)}},
                }
            },
            "/api/v1/me/lesson-drafts/latest/": {
                "get": {
                    "operationId": "getLatestLessonDraft",
                    "summary": "Get the learner's latest unfinished lesson draft",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Latest owner-scoped draft or null"), **private_errors},
                }
            },
            "/api/v1/me/lesson-drafts/{lesson_id}/": {
                "parameters": [{"name": "lesson_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 100}}],
                "put": {
                    "operationId": "putLessonDraft",
                    "summary": "Save bounded progress for one unfinished lesson",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/LessonDraftRequest"}}}},
                    "responses": {"200": _json_response("Draft saved"), **{str(code): error_response for code in (400, 401, 404, 413, 415, 429, 503)}},
                },
                "delete": {
                    "operationId": "deleteLessonDraft",
                    "summary": "Delete one owner-scoped lesson draft",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Draft removed"), **{str(code): error_response for code in (401, 404, 429, 503)}},
                },
            },
            "/api/v1/me/sm2/": {
                "get": {
                    "operationId": "getLearnerSm2",
                    "summary": "Get the learner's personal SM-2 queue",
                    "security": [{"supabaseBearer": []}, {"browserSession": []}],
                    "responses": {"200": _json_response("Owner-scoped SM-2 queue"), **private_errors},
                }
            },
            "/api/v1/me/sm2/{word_id}/review/": {
                "parameters": [{"name": "word_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}],
                "post": {
                    "operationId": "reviewLearnerSm2Word",
                    "summary": "Schedule one owned dictionary word with SM-2",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Sm2ReviewRequest"}}}},
                    "responses": {"200": _json_response("Updated owner-scoped review schedule"), **{str(code): error_response for code in (400, 401, 404, 413, 415, 429, 503)}},
                },
            },
            "/api/v1/me/reading-bookmarks/": {"get": {"operationId": "getReadingBookmarks", "summary": "Get saved reading text IDs", "security": [{"supabaseBearer": []}, {"browserSession": []}], "responses": {"200": _json_response("Owner-scoped reading bookmarks"), **private_errors}}},
            "/api/v1/me/reading-bookmarks/{text_id}/": {
                "parameters": [{"name": "text_id", "in": "path", "required": True, "schema": {"type": "string", "maxLength": 80}}],
                "put": {"operationId": "saveReadingBookmark", "summary": "Save a reading text", "security": [{"supabaseBearer": []}], "responses": {"200": _json_response("Bookmark saved"), **{str(code): error_response for code in (401, 404, 429, 503)}}},
                "delete": {"operationId": "deleteReadingBookmark", "summary": "Remove a reading text", "security": [{"supabaseBearer": []}], "responses": {"200": _json_response("Bookmark removed"), **{str(code): error_response for code in (401, 404, 429, 503)}}},
            },
            "/api/v1/me/dictionary/{word_id}/": {
                "parameters": [{"name": "word_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}],
                "delete": {
                    "operationId": "deleteLearnerDictionaryWord",
                    "summary": "Delete one owner-scoped personal dictionary word",
                    "security": [{"supabaseBearer": []}],
                    "responses": {"200": _json_response("Dictionary word removed"), **{str(code): error_response for code in (401, 429, 503)}},
                },
            },
            "/api/v1/me/lesson-results/": {
                "post": {
                    "operationId": "postLessonResult",
                    "summary": "Store an idempotent lesson-result event for a native client",
                    "security": [{"supabaseBearer": []}],
                    "requestBody": _lesson_result_body(),
                    "responses": {
                        "200": _json_response("Duplicate event confirmed"),
                        "201": _json_response("Event created"),
                        **{str(code): error_response for code in (400, 401, 404, 409, 413, 415, 429, 503)},
                    },
                }
            },
            "/api/v1/me/lesson-results/session/": {
                "post": {
                    "operationId": "postBrowserLessonResult",
                    "summary": "Store a queued browser result without exposing the HttpOnly token",
                    "security": [{"browserSession": [], "csrfHeader": []}],
                    "requestBody": _lesson_result_body(),
                    "responses": {
                        "200": _json_response("Duplicate event confirmed"),
                        "201": _json_response("Event created"),
                        **{str(code): error_response for code in (400, 401, 403, 404, 409, 413, 415, 503)},
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "supabaseBearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Supabase access token; never persist it in an offline event queue.",
                },
                "browserSession": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "polskiflow_access_token",
                    "description": "HttpOnly browser session cookie managed by LingoFlow.",
                },
                "csrfHeader": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-CSRFToken",
                },
            },
            "schemas": {
                "ProfilePatchRequest": {
                    "type": "object", "additionalProperties": False, "minProperties": 1,
                    "properties": {
                        "display_name": {"type": "string", "minLength": 1, "maxLength": 80},
                        "level": {"type": "string", "enum": ["A1", "A2", "B1", "B2", "C1", "C2"]},
                        "daily_goal_lessons": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                },
                "ReminderPreferencesPatchRequest": {
                    "type": "object", "additionalProperties": False, "minProperties": 1,
                    "properties": {
                        "daily_reminder_enabled": {"type": "boolean"},
                        "reminder_time": {"type": "string", "pattern": "^(?:[01]\\d|2[0-3]):[0-5]\\d$"},
                    },
                },
                "FeedbackRequest": {
                    "type": "object", "additionalProperties": False,
                    "required": ["category", "message"],
                    "properties": {
                        "category": {"type": "string", "enum": ["content", "translation", "interface", "technical", "idea"]},
                        "message": {"type": "string", "minLength": 20, "maxLength": 2000},
                        "page_url": {"type": "string", "maxLength": 300},
                        "priority": {"type": "string", "enum": ["normal", "high", "blocking"], "default": "normal"},
                    },
                },
                "GlossaryWordRequest": {
                    "type": "object", "additionalProperties": False,
                    "required": ["surface"],
                    "properties": {"surface": {"type": "string", "minLength": 1, "maxLength": 160}},
                },
                "Sm2ReviewRequest": {
                    "type": "object", "additionalProperties": False,
                    "required": ["quality"],
                    "properties": {"quality": {"type": "string", "enum": ["again", "hard", "good", "easy"]}},
                },
                "LessonAnswerRequest": {
                    "oneOf": [
                        {"type": "object", "additionalProperties": False, "required": ["position", "selected_index"], "properties": {"position": {"type": "integer", "minimum": 0}, "selected_index": {"type": "integer", "minimum": 0}}},
                        {"type": "object", "additionalProperties": False, "required": ["position", "token_order"], "properties": {"position": {"type": "integer", "minimum": 0}, "token_order": {"type": "array", "items": {"type": "integer", "minimum": 0}}}},
                    ]
                },
                "ListeningAnswerRequest": {
                    "type": "object", "additionalProperties": False,
                    "required": ["question_id", "selected_index"],
                    "properties": {
                        "question_id": {"type": "string", "minLength": 1, "maxLength": 80},
                        "selected_index": {"type": "integer", "minimum": 0},
                    },
                },
                "InteractionAnswerRequest": {
                    "oneOf": [
                        {"type": "object", "additionalProperties": False, "required": ["option_id"], "properties": {"option_id": {"type": "string", "minLength": 1, "maxLength": 40}}},
                        {"type": "object", "additionalProperties": False, "required": ["block_ids"], "properties": {"block_ids": {"type": "array", "minItems": 1, "maxItems": 10, "uniqueItems": True, "items": {"type": "string", "minLength": 1, "maxLength": 40}}}},
                    ]
                },
                "DiagnosticRequest": {
                    "type": "object", "additionalProperties": False,
                    "required": ["self_ratings", "answers"],
                    "properties": {
                        "self_ratings": {
                            "type": "object", "additionalProperties": False,
                            "required": ["reception", "production", "interaction", "mediation"],
                            "properties": {key: {"type": "string", "enum": ["0", "1", "2", "3", "4", "5"]} for key in ("reception", "production", "interaction", "mediation")},
                        },
                        "answers": {
                            "type": "object", "additionalProperties": False,
                            "required": [f"check_{index}" for index in range(1, 9)],
                            "properties": {f"check_{index}": {"type": "string", "enum": ["a", "b", "c"]} for index in range(1, 9)},
                        },
                    },
                },
                "WritingCheckRequest": {
                    "type": "object", "additionalProperties": False,
                    "required": ["text"],
                    "properties": {"text": {"type": "string", "minLength": 1, "maxLength": 16000}},
                },
                "AccountDeletionRequest": {
                    "type": "object", "additionalProperties": False,
                    "required": ["password"],
                    "properties": {"password": {"type": "string", "minLength": 1, "maxLength": 1024, "format": "password"}},
                },
                "LessonDraftRequest": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["step_index", "score"],
                    "properties": {
                        "step_index": {"type": "integer", "minimum": 1},
                        "score": {"type": "integer", "minimum": 0},
                    },
                },
                "LessonResultRequest": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "event_id", "lesson_id", "plan_date", "completed_at",
                        "cards_total", "cards_known", "contract_version",
                    ],
                    "properties": {
                        "event_id": {"type": "string", "format": "uuid"},
                        "lesson_id": {"type": "string", "minLength": 1, "maxLength": 100},
                        "plan_date": {"type": "string", "format": "date"},
                        "completed_at": {"type": "string", "format": "date-time"},
                        "cards_total": {"type": "integer", "minimum": 0},
                        "cards_known": {"type": "integer", "minimum": 0},
                        "contract_version": {"type": "string", "const": "1.0"},
                        "client_instance_id": {"type": "string", "maxLength": 100},
                    },
                },
                "ErrorEnvelope": {
                    "type": "object",
                    "required": ["api_version", "error"],
                    "properties": {
                        "api_version": {"type": "string", "const": "v1"},
                        "error": {
                            "type": "object",
                            "required": ["code", "detail"],
                            "properties": {
                                "code": {"type": "string"},
                                "detail": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    }


def _json_response(description):
    return {
        "description": description,
        "content": {"application/json": {"schema": {"type": "object"}}},
    }


def _lesson_result_body():
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/LessonResultRequest"}
            }
        },
    }
