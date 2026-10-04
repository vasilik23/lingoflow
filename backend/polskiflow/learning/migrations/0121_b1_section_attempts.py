import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0120_b1_mock_attempt_id")]

    operations = [
        migrations.CreateModel(
            name="B1SectionAttempt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("user_id", models.UUIDField()),
                ("attempt_id", models.UUIDField(default=uuid.uuid4)),
                ("attempted_at", models.DateTimeField(auto_now_add=True)),
                ("attempt_version", models.CharField(max_length=32)),
                ("section_id", models.CharField(max_length=16)),
                ("correct", models.PositiveSmallIntegerField()),
                ("total", models.PositiveSmallIntegerField()),
            ],
            options={"db_table": "b1_section_attempts", "managed": False},
        ),
        migrations.AddConstraint(
            model_name="b1sectionattempt",
            constraint=models.UniqueConstraint(
                fields=("user_id", "attempt_id"),
                name="b1_section_attempts_user_attempt_key",
            ),
        ),
    ]
