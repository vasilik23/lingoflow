import uuid
from datetime import date

from django.db import models


class Level(models.TextChoices):
    A1 = "A1", "A1"
    A2 = "A2", "A2"
    B1 = "B1", "B1"
    B2 = "B2", "B2"
    C1 = "C1", "C1"
    C2 = "C2", "C2"


class LessonKind(models.TextChoices):
    WORDS = "words", "Новые слова"
    GRAMMAR = "grammar", "Грамматика"
    REVIEW = "review", "Повторение"
    QUIZ = "quiz", "Мини-тест"


class Course(models.Model):
    id = models.SlugField(primary_key=True, max_length=64)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=2, choices=Level.choices, default=Level.A1)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "courses"
        ordering = ("position", "id")

    def __str__(self):
        return f"{self.level} · {self.title}"


class Topic(models.Model):
    id = models.SlugField(primary_key=True, max_length=80)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    emoji = models.CharField(max_length=8, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "topics"
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("course", "position"), name="unique_topic_position"
            )
        ]

    def __str__(self):
        return f"{self.course.level} · {self.title}"


class Lesson(models.Model):
    id = models.SlugField(primary_key=True, max_length=32)
    title = models.CharField(max_length=120)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        related_name="lessons",
        blank=True,
        null=True,
    )
    kind = models.CharField(
        max_length=16, choices=LessonKind.choices, default=LessonKind.WORDS
    )
    plan_title = models.CharField(max_length=120)
    subtitle = models.CharField(max_length=160)
    description = models.TextField()
    minutes = models.PositiveSmallIntegerField(default=5)
    emoji = models.CharField(max_length=8, blank=True)
    theory_title = models.CharField(max_length=160, blank=True)
    theory_sections = models.JSONField(default=list, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "lessons"
        ordering = ("position", "id")

    def __str__(self):
        return self.title


class Flashcard(models.Model):
    id = models.SlugField(primary_key=True, max_length=80)
    polish = models.CharField(max_length=160)
    translation = models.CharField(max_length=240)
    example = models.TextField(blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "flashcards"
        ordering = ("position", "id")

    def __str__(self):
        return f"{self.polish} — {self.translation}"


class LessonFlashcard(models.Model):
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="flashcard_links"
    )
    flashcard = models.ForeignKey(
        Flashcard, on_delete=models.CASCADE, related_name="lesson_links"
    )
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "lesson_flashcards"
        ordering = ("position", "flashcard_id")
        constraints = [
            models.UniqueConstraint(
                fields=("lesson", "flashcard"), name="unique_lesson_flashcard"
            ),
            models.UniqueConstraint(
                fields=("lesson", "position"),
                name="unique_lesson_flashcard_position",
            ),
        ]


class ReadingText(models.Model):
    id = models.SlugField(primary_key=True, max_length=80)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        related_name="reading_texts",
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=160)
    description = models.CharField(max_length=240)
    level = models.CharField(max_length=2, choices=Level.choices, default=Level.A1)
    minutes = models.PositiveSmallIntegerField(default=5)
    emoji = models.CharField(max_length=8, blank=True)
    paragraphs = models.JSONField(default=list)
    glossary = models.JSONField(default=dict)
    source_metadata = models.JSONField(default=dict, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "reading_texts"
        ordering = ("position", "id")

    def __str__(self):
        return f"{self.level} · {self.title}"


class Question(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    options = models.JSONField(default=list)
    correct = models.PositiveSmallIntegerField()
    explanation = models.TextField(blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "questions"
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("lesson", "position"), name="unique_question_position"
            )
        ]

    def __str__(self):
        return self.prompt


class Profile(models.Model):
    id = models.UUIDField(primary_key=True)
    display_name = models.TextField(blank=True, null=True)
    level = models.CharField(max_length=2, choices=Level.choices, default=Level.A1)
    daily_goal_lessons = models.PositiveSmallIntegerField(default=4)
    streak_days = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "profiles"
        managed = False


class LessonCompletion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    lesson_id = models.CharField(max_length=80)
    plan_date = models.DateField()
    cards_total = models.PositiveIntegerField(default=0)
    cards_known = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField()

    class Meta:
        db_table = "lesson_completions"
        managed = False
        constraints = [
            models.UniqueConstraint(
                fields=("user_id", "lesson_id", "plan_date"),
                name="unique_daily_lesson_completion",
            ),
            models.CheckConstraint(
                condition=models.Q(cards_known__lte=models.F("cards_total")),
                name="cards_known_not_above_total",
            ),
        ]


class LessonDraft(models.Model):
    pk = models.CompositePrimaryKey("user_id", "lesson_id")
    user_id = models.UUIDField()
    lesson_id = models.TextField()
    lesson_kind = models.CharField(max_length=16)
    step_index = models.PositiveSmallIntegerField(default=0)
    score = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "lesson_drafts"
        managed = False


class LearnerMistake(models.Model):
    pk = models.CompositePrimaryKey("user_id", "lesson_id", "question_position")
    user_id = models.UUIDField()
    lesson_id = models.TextField()
    question_position = models.PositiveSmallIntegerField()
    last_wrong_at = models.DateTimeField()

    class Meta:
        db_table = "learner_mistakes"
        managed = False


class LessonNote(models.Model):
    pk = models.CompositePrimaryKey("user_id", "lesson_id")
    user_id = models.UUIDField()
    lesson_id = models.TextField()
    body = models.TextField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "lesson_notes"
        managed = False


class LearningCollection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    name = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "learning_collections"
        managed = False


class LearningCollectionItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection_id = models.UUIDField()
    user_id = models.UUIDField()
    content_type = models.CharField(max_length=16)
    content_id = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "learning_collection_items"
        managed = False


class FlashcardReview(models.Model):
    pk = models.CompositePrimaryKey("user_id", "card_id")
    user_id = models.UUIDField()
    card_id = models.TextField()
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.PositiveIntegerField(default=0)
    repetitions = models.PositiveIntegerField(default=0)
    next_review_date = models.DateField(default=date.today)
    last_reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "flashcard_reviews"
        managed = False
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ease_factor__gte=1.3),
                name="flashcard_review_minimum_ease",
            )
        ]


class PersonalWord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    word = models.CharField(max_length=160)
    translation = models.CharField(max_length=240)
    context = models.TextField(blank=True)
    source_text_id = models.CharField(max_length=80, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.PositiveIntegerField(default=0)
    repetitions = models.PositiveIntegerField(default=0)
    next_review_date = models.DateField(default=date.today)
    last_reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "personal_words"
        managed = False
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user_id", "word"), name="unique_personal_word"
            ),
            models.CheckConstraint(
                condition=models.Q(ease_factor__gte=1.3),
                name="personal_word_minimum_ease",
            ),
        ]


class LessonResultEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    event_id = models.UUIDField()
    payload_hash = models.CharField(max_length=64)
    lesson_id = models.CharField(max_length=32)
    plan_date = models.DateField()
    completed_at = models.DateTimeField()
    cards_total = models.PositiveIntegerField()
    cards_known = models.PositiveIntegerField()
    contract_version = models.CharField(max_length=16)
    client_instance_id = models.CharField(max_length=128, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lesson_result_events"
        managed = False
        indexes = [
            models.Index(fields=("lesson_id",), name="result_events_lesson_idx")
        ]


class ReadingBookmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    reading_text_id = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reading_bookmarks"
        managed = False


class LessonBookmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    lesson_id = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lesson_bookmarks"
        managed = False


class UserFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    category = models.CharField(max_length=24)
    message = models.TextField()
    page_url = models.CharField(max_length=300, blank=True)
    priority = models.CharField(max_length=16, default="normal")
    status = models.CharField(max_length=16, default="new")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_feedback"
        managed = False


class ReminderPreference(models.Model):
    user_id = models.UUIDField(primary_key=True)
    daily_reminder_enabled = models.BooleanField(default=False)
    reminder_time = models.TimeField(default="19:00")
    timezone = models.CharField(max_length=64, default="Europe/Warsaw")
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "reminder_preferences"
        managed = False


class B1MockAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    attempt_id = models.UUIDField(default=uuid.uuid4)
    attempted_at = models.DateTimeField(auto_now_add=True)
    attempt_version = models.CharField(max_length=32, default="b1-weekly-v1")
    listening_correct = models.PositiveSmallIntegerField()
    reading_correct = models.PositiveSmallIntegerField()
    grammar_correct = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "b1_mock_attempts"
        managed = False
        constraints = [
            models.UniqueConstraint(
                fields=("user_id", "attempt_id"),
                name="b1_mock_attempts_user_attempt_key",
            ),
        ]
