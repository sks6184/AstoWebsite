from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="answer_language",
            field=models.CharField(default="English", max_length=40),
        ),
    ]
