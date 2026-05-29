from django.db import models


class TrafficPrediction(models.Model):
    zone = models.CharField(max_length=100)
    predicted_congestion = models.PositiveSmallIntegerField()
    rain_probability = models.PositiveSmallIntegerField()
    confidence = models.DecimalField(max_digits=5, decimal_places=2)
    predicted_for = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["zone", "predicted_for"])]

    def __str__(self):
        return f"{self.zone} {self.predicted_congestion}%"
