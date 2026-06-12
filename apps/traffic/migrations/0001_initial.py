from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="TrafficRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("zone", models.CharField(max_length=100)),
                ("latitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("longitude", models.DecimalField(decimal_places=6, max_digits=9)),
                ("congestion_level", models.PositiveSmallIntegerField()),
                ("average_speed", models.DecimalField(decimal_places=2, max_digits=5)),
                ("recorded_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddIndex(model_name="trafficrecord", index=models.Index(fields=["zone", "recorded_at"], name="traffic_tra_zone_318867_idx")),
    ]
