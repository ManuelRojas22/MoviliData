from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="CityMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=80)),
                ("value", models.DecimalField(decimal_places=2, max_digits=10)),
                ("unit", models.CharField(blank=True, max_length=20)),
                ("trend", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["label"]},
        ),
    ]
