# Generated by Django 3.2.16 on 2022-11-04 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0020_editfuturepaymentlogentry_comment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="editfuturepaymentlogentry",
            name="comment",
            field=models.CharField(max_length=256),
        ),
    ]