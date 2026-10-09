from django.http import JsonResponse
from django.urls import path
from django.contrib import admin
from django.views.i18n import set_language

from polskiflow.api_views import catalog_v1, learner_account_v1, learner_achievements_v1, learner_bootstrap_v1, learner_data_export_v1, learner_feedback_v1, learner_history_v1, learner_latest_lesson_draft_v1, learner_lesson_draft_v1, learner_profile_v1, learner_progress_v1, learner_reading_bookmark_v1, learner_reading_bookmarks_v1, learner_reminder_preferences_v1, learner_sm2_review_v1, learner_sm2_v1, learner_today_v1, lesson_results_session_v1, lesson_results_v1, native_diagnostic_evaluate_v1, native_diagnostic_v1, native_dictionary_word_v1, native_interaction_answer_v1, native_interaction_v1, native_lesson_answer_v1, native_lesson_v1, native_listening_answer_v1, native_listening_v1, native_reading_detail_v1, native_reading_dictionary_v1, native_reading_library_v1, native_writing_check_v1, native_writing_v1, news_v1, openapi_v1
from polskiflow.account_views import account_delete, account_security
from polskiflow.auth import require_supabase_user
from polskiflow.auth_views import b1_exam_prep, course, daily_tasks, forgot_password, help_center, home, listening_practice, login_view, logout_view, onboarding, practice_hub, privacy, profile, profile_data_export, register_view, resend_confirmation, reset_password, sources, writing_practice
from polskiflow.diagnostic_views import diagnostic
from polskiflow.placement_views import placement_check
from polskiflow.public_views import public_intro, public_demo
from polskiflow.feedback_views import feedback
from polskiflow.ai_writing_views import ai_writing_review
from polskiflow.b1_writing_views import exam_writing
from polskiflow.history_views import learning_history
from polskiflow.lesson_views import lesson, lesson_note, lesson_step
from polskiflow.interaction_views import interaction_practice
from polskiflow.learning_space_views import learning_space
from polskiflow.operational_views import health, readiness
from polskiflow.pwa_views import offline_shell, service_worker, web_app_manifest
from polskiflow.reading_views import (
    add_dictionary_word,
    dictionary,
    dictionary_practice,
    dictionary_practice_step,
    news_library,
    reader,
    reading_library,
    toggle_reading_bookmark,
    remove_dictionary_word,
)
from polskiflow.search_views import global_search
from polskiflow.saved_views import saved_learning, toggle_lesson_bookmark
from polskiflow.mistake_views import mistake_notebook, mistake_practice
from polskiflow.note_views import delete_lesson_note, lesson_notes
from polskiflow.collection_views import add_material_to_collection, collection_action, collections, create_collection_view, remove_collection_item
from polskiflow.beta_views import beta_center
from polskiflow.b1_mock_views import b1_exam_simulation, b1_weekly_mock
from polskiflow.b1_run_views import b1_training_run


@require_supabase_user
def current_user(request):
    return JsonResponse(
        {"id": request.supabase_user.id, "email": request.supabase_user.email}
    )


urlpatterns = [
    path("language/", set_language, name="set-language"),
    path("admin/", admin.site.urls),
    path("manifest.webmanifest", web_app_manifest, name="web-app-manifest"),
    path("service-worker.js", service_worker, name="service-worker"),
    path("offline/", offline_shell, name="offline-shell"),
    path("", home, name="home"),
    path("tasks/", daily_tasks, name="daily-tasks"),
    path("course/", course, name="course"),
    path("practice/", practice_hub, name="practice-hub"),
    path("exam/b1/run/", b1_training_run, name="b1-training-run"),
    path("exam/b1/", b1_exam_prep, name="b1-exam-prep"),
    path("exam/b1/mock/", b1_weekly_mock, name="b1-weekly-mock"),
    path("exam/b1/simulation/", b1_exam_simulation, name="b1-exam-simulation"),
    path("my-learning/", learning_space, name="learning-space"),
    path("welcome/", onboarding, name="onboarding"),
    path("welcome/check/", placement_check, name="placement-check"),
    path("start/", public_intro, name="public-intro"),
    path("demo/", public_demo, name="public-demo"),
    path("search/", global_search, name="global-search"),
    path("saved/", saved_learning, name="saved-learning"),
    path("mistakes/", mistake_notebook, name="mistake-notebook"),
    path("mistakes/practice/", mistake_practice, name="mistake-practice"),
    path("notes/", lesson_notes, name="lesson-notes"),
    path("notes/<slug:lesson_id>/delete/", delete_lesson_note, name="delete-lesson-note"),
    path("collections/", collections, name="collections"),
    path("collections/create/", create_collection_view, name="create-collection"),
    path("collections/<uuid:collection_id>/", collection_action, name="collection-action"),
    path("collections/items/<uuid:item_id>/remove/", remove_collection_item, name="remove-collection-item"),
    path("collections/add/<str:content_type>/<slug:content_id>/", add_material_to_collection, name="add-material-to-collection"),
    path("diagnostic/", diagnostic, name="diagnostic"),
    path("profile/", profile, name="profile"),
    path("settings/", profile, {"section": "settings"}, name="system-settings"),
    path("help/", help_center, name="help-center"),
    path("account/security/", account_security, name="account-security"),
    path("account/delete/", account_delete, name="account-delete"),
    path("feedback/", feedback, name="feedback"),
    path("beta/", beta_center, name="beta-center"),
    path("history/", learning_history, name="learning-history"),
    path("profile/export/", profile_data_export, name="profile-data-export"),
    path("writing/ai-review/", ai_writing_review, name="ai-writing-review"),
    path("writing/exam/b1/", exam_writing, name="b1-exam-writing"),
    path("writing/", writing_practice, name="writing-practice"),
    path("interaction/", interaction_practice, name="interaction-practice"),
    path("listening/", listening_practice, name="listening-practice"),
    path("sources/", sources, name="sources"),
    path("privacy/", privacy, name="privacy"),
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("forgot-password/", forgot_password, name="forgot-password"),
    path("reset-password/", reset_password, name="reset-password"),
    path("resend-confirmation/", resend_confirmation, name="resend-confirmation"),
    path("logout/", logout_view, name="logout"),
    path("lesson/<slug:lesson_id>/", lesson, name="lesson"),
    path("lesson/<slug:lesson_id>/bookmark/", toggle_lesson_bookmark, name="toggle-lesson-bookmark"),
    path("lesson/<slug:lesson_id>/step/", lesson_step, name="lesson-step"),
    path("lesson/<slug:lesson_id>/note/", lesson_note, name="lesson-note"),
    path("reading/", reading_library, name="reading-library"),
    path("news/", news_library, name="news-library"),
    path("reading/<slug:text_id>/", reader, name="reader"),
    path("reading/<slug:text_id>/bookmark/", toggle_reading_bookmark, name="toggle-reading-bookmark"),
    path("reading/<slug:text_id>/save/", add_dictionary_word, name="add-dictionary-word"),
    path("dictionary/", dictionary, name="dictionary"),
    path("dictionary/practice/", dictionary_practice, name="dictionary-practice"),
    path("dictionary/practice/step/", dictionary_practice_step, name="dictionary-practice-step"),
    path("dictionary/<uuid:word_id>/delete/", remove_dictionary_word, name="remove-dictionary-word"),
    path("health/", health, name="health"),
    path("ready/", readiness, name="readiness"),
    path("api/auth/me/", current_user, name="current-user"),
    path("api/v1/catalog/", catalog_v1, name="api-v1-catalog"),
    path("api/v1/news/", news_v1, name="api-v1-news"),
    path("api/v1/lessons/<slug:lesson_id>/", native_lesson_v1, name="api-v1-native-lesson"),
    path("api/v1/lessons/<slug:lesson_id>/answer/", native_lesson_answer_v1, name="api-v1-native-lesson-answer"),
    path("api/v1/listening/", native_listening_v1, name="api-v1-native-listening"),
    path("api/v1/listening/<slug:exercise_id>/answer/", native_listening_answer_v1, name="api-v1-native-listening-answer"),
    path("api/v1/interaction/", native_interaction_v1, name="api-v1-native-interaction"),
    path("api/v1/interaction/<slug:scenario_id>/answer/", native_interaction_answer_v1, name="api-v1-native-interaction-answer"),
    path("api/v1/diagnostic/", native_diagnostic_v1, name="api-v1-native-diagnostic"),
    path("api/v1/diagnostic/evaluate/", native_diagnostic_evaluate_v1, name="api-v1-native-diagnostic-evaluate"),
    path("api/v1/writing/", native_writing_v1, name="api-v1-native-writing"),
    path("api/v1/writing/<slug:prompt_id>/check/", native_writing_check_v1, name="api-v1-native-writing-check"),
    path("api/v1/reading/", native_reading_library_v1, name="api-v1-native-reading-library"),
    path("api/v1/reading/<slug:text_id>/", native_reading_detail_v1, name="api-v1-native-reading-detail"),
    path("api/v1/reading/<slug:text_id>/dictionary/", native_reading_dictionary_v1, name="api-v1-native-reading-dictionary"),
    path("api/v1/openapi.json", openapi_v1, name="api-v1-openapi"),
    path("api/v1/me/progress/", learner_progress_v1, name="api-v1-learner-progress"),
    path("api/v1/me/profile/", learner_profile_v1, name="api-v1-learner-profile"),
    path("api/v1/me/account/", learner_account_v1, name="api-v1-learner-account"),
    path("api/v1/me/export/", learner_data_export_v1, name="api-v1-learner-data-export"),
    path("api/v1/me/reminder-preferences/", learner_reminder_preferences_v1, name="api-v1-learner-reminder-preferences"),
    path("api/v1/me/feedback/", learner_feedback_v1, name="api-v1-learner-feedback"),
    path("api/v1/me/today/", learner_today_v1, name="api-v1-learner-today"),
    path("api/v1/me/bootstrap/", learner_bootstrap_v1, name="api-v1-learner-bootstrap"),
    path("api/v1/me/achievements/", learner_achievements_v1, name="api-v1-learner-achievements"),
    path("api/v1/me/history/", learner_history_v1, name="api-v1-learner-history"),
    path("api/v1/me/lesson-drafts/latest/", learner_latest_lesson_draft_v1, name="api-v1-latest-lesson-draft"),
    path("api/v1/me/lesson-drafts/<slug:lesson_id>/", learner_lesson_draft_v1, name="api-v1-lesson-draft"),
    path("api/v1/me/sm2/", learner_sm2_v1, name="api-v1-learner-sm2"),
    path("api/v1/me/sm2/<uuid:word_id>/review/", learner_sm2_review_v1, name="api-v1-learner-sm2-review"),
    path("api/v1/me/dictionary/<uuid:word_id>/", native_dictionary_word_v1, name="api-v1-native-dictionary-word"),
    path("api/v1/me/reading-bookmarks/", learner_reading_bookmarks_v1, name="api-v1-reading-bookmarks"),
    path("api/v1/me/reading-bookmarks/<slug:text_id>/", learner_reading_bookmark_v1, name="api-v1-reading-bookmark"),
    path("api/v1/me/lesson-results/", lesson_results_v1, name="api-v1-lesson-results"),
    path("api/v1/me/lesson-results/session/", lesson_results_session_v1, name="api-v1-lesson-results-session"),
]
