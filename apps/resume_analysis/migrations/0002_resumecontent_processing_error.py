# Generated by Django 5.1.6 on 2025-03-28 00:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resume_analysis", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="resumecontent",
            name="processing_error",
            field=models.TextField(blank=True, null=True),
        ),
    ]
