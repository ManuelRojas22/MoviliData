from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="SafeRoute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("origin", models.CharField(max_length=120)),
                ("destination", models.CharField(max_length=120)),
                ("distance_km", models.DecimalField(decimal_places=2, max_digits=6)),
                ("estimated_minutes", models.PositiveSmallIntegerField()),
                ("risk_score", models.PositiveSmallIntegerField()),
                ("active", models.BooleanField(default=True)),
            ],
        ),
    ]
