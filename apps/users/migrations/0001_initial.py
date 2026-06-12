from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.PositiveIntegerField(unique=True)),
                ("role", models.CharField(default="Analista de movilidad", max_length=60)),
                ("organization", models.CharField(default="MoviliData OS", max_length=120)),
            ],
        ),
    ]
