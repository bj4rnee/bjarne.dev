from django.db import models

class VisitCounter(models.Model):
    count = models.PositiveIntegerField(default=0)