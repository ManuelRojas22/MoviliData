from django.db import models


class UserProfile(models.Model):
    user_id = models.PositiveIntegerField(unique=True)
    role = models.CharField(max_length=60, default="Analista de movilidad")
    organization = models.CharField(max_length=120, default="MoviliData OS")

    def __str__(self):
        return self.organization
