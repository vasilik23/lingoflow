from django.apps import AppConfig


class LearningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "polskiflow.learning"
    verbose_name = "Обучение"

    def ready(self):
        from . import recording_checks  # noqa: F401
