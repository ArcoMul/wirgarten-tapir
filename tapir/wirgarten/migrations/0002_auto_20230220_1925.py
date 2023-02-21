# Generated by Django 3.2.17 on 2023-02-20 18:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="consent_ts",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["type"], name="idx_product_type"),
        ),
    ]
