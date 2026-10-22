"""Contextual deposit definitions and the remaining A1 infinitive; no approval."""
from django.db import migrations

OPTIONS = ["плата за отопление","сумма, внесённая как обеспечение при аренде","прибор для измерения расхода электричества"]
ENTRY = {"lemma":"zapraszać","translation":"прошу / проходите","part_of_speech":"глагол"}


def seed(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return
    Question = apps.get_model('learning', 'Question')
    Reading = apps.get_model('learning', 'ReadingText')
    Question.objects.filter(lesson_id='housing-quiz', position=0, correct=1).update(options=OPTIONS)
    reading = Reading.objects.get(pk='pierwszy-dzien-na-kursie')
    reading.glossary = {**reading.glossary, 'zapraszam': ENTRY}
    reading.save(update_fields=['glossary'])


class Migration(migrations.Migration):
    dependencies = [('learning', '0126_pilot_editorial_corrections')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
