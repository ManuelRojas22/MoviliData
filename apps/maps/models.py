from django.db import models


class RiskZone(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    risk_score = models.PositiveSmallIntegerField()
    reason = models.CharField(max_length=180)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["risk_score"])]

    def __str__(self):
        return self.name
