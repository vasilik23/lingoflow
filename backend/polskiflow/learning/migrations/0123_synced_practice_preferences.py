from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('learning', '0122_b1_run_attempts')]
    operations = [migrations.AddField(
        model_name='profile', name='practice_exclude_remote_work',
        field=models.BooleanField(null=True, blank=True),
    )]
