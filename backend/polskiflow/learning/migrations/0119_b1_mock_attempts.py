import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0118_user_feedback_priority")]
    operations = [
        migrations.CreateModel(
            name="B1MockAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("user_id", models.UUIDField()),
                ("attempted_at", models.DateTimeField(auto_now_add=True)),
                ("attempt_version", models.CharField(default="b1-weekly-v1", max_length=32)),
                ("listening_correct", models.PositiveSmallIntegerField()),
                ("reading_correct", models.PositiveSmallIntegerField()),
                ("grammar_correct", models.PositiveSmallIntegerField()),
            ],
            options={"db_table": "b1_mock_attempts", "managed": False},
        ),
    ]
