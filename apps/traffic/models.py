from django.db import models


class TrafficRecord(models.Model):
    zone = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    congestion_level = models.PositiveSmallIntegerField()
    average_speed = models.DecimalField(max_digits=5, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["zone", "recorded_at"])]

    def __str__(self):
        return f"{self.zone} {self.congestion_level}%"
