# Generated by Django 3.2.15 on 2022-10-07 12:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tapirparameter",
            name="label",
            field=models.CharField(default="", max_length=256),
            preserve_default=False,
        ),
    ]