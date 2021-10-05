# Generated by Django 3.1.13 on 2021-10-05 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shifts", "0025_auto_20211003_1502"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ShiftCycleLog",
            new_name="ShiftCycleEntry",
        ),
        migrations.AlterModelOptions(
            name="shiftexemption",
            options={"ordering": ["-start_date"]},
        ),
        migrations.AlterField(
            model_name="shiftexemption",
            name="end_date",
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="shiftexemption",
            name="start_date",
            field=models.DateField(db_index=True),
        ),
    ]
