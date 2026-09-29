from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0117_learning_collections")]
    operations = [
        migrations.AddField(
            model_name="userfeedback",
            name="priority",
            field=models.CharField(default="normal", max_length=16),
        )
    ]
