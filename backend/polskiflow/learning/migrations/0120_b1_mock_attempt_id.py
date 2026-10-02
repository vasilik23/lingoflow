import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0119_b1_mock_attempts")]

    operations = [
        migrations.AddField(
            model_name="b1mockattempt",
            name="attempt_id",
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AddConstraint(
            model_name="b1mockattempt",
            constraint=models.UniqueConstraint(
                fields=("user_id", "attempt_id"),
                name="b1_mock_attempts_user_attempt_key",
            ),
        ),
    ]
