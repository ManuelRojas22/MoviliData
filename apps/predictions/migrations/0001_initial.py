from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="TrafficPrediction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("zone", models.CharField(max_length=100)),
                ("predicted_congestion", models.PositiveSmallIntegerField()),
                ("rain_probability", models.PositiveSmallIntegerField()),
                ("confidence", models.DecimalField(decimal_places=2, max_digits=5)),
                ("predicted_for", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddIndex(model_name="trafficprediction", index=models.Index(fields=["zone", "predicted_for"], name="prediction_zone_time_idx")),
    ]
