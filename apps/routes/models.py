from django.db import models


class SafeRoute(models.Model):
    name = models.CharField(max_length=120)
    origin = models.CharField(max_length=120)
    destination = models.CharField(max_length=120)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2)
    estimated_minutes = models.PositiveSmallIntegerField()
    risk_score = models.PositiveSmallIntegerField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
