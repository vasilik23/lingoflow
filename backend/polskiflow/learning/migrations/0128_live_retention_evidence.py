from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('learning', '0127_pilot_editorial_recheck')]
    operations = [
        migrations.AddField(model_name='profile', name='last_request_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='profile', name='activity_tracking_started_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='userfeedback', name='closed_at', field=models.DateTimeField(blank=True, null=True)),
    ]
