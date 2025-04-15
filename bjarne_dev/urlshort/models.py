from django.db import models


class Shorted_url(models.Model):
    original_url = models.TextField(max_length=2048, unique=True)
    hash = models.CharField(max_length=10, unique=True)
    creation_date = models.DateTimeField('creation date')