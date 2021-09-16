# Generated by Django 3.1.13 on 2021-09-14 10:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shifts", "0016_auto_20210907_2036"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shiftattendance",
            name="state",
            field=models.IntegerField(
                choices=[
                    (1, "Pending"),
                    (2, "Done"),
                    (3, "Cancelled"),
                    (4, "Missed"),
                    (5, "Missed Excused"),
                    (6, "Looking For Stand In"),
                ],
                default=1,
            ),
        ),
    ]