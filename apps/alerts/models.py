from django.db import models


class MobilityAlert(models.Model):
    LEVELS = [("alta", "Alta"), ("media", "Media"), ("baja", "Baja")]
    title = models.CharField(max_length=140)
    zone = models.CharField(max_length=100)
    level = models.CharField(max_length=10, choices=LEVELS)
    description = models.TextField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
