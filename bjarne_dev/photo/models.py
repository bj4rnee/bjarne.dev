from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone

from . import storage

ORIENTATION_CHOICES = [
    ('landscape', 'landscape'),
    ('portrait', 'portrait'),
    ('square', 'square'),
]


class Collection(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    description = models.TextField(blank=True)
    # optional explicit cover, but falls back to the newest published photo
    cover = models.ForeignKey(
        'Photograph', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+')
    display_order = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def cover_photo(self):
        if self.cover and self.cover.published:
            return self.cover
        return self.photographs.filter(published=True).first()

    def published_count(self):
        return self.photographs.filter(published=True).count()


class Photograph(models.Model):
    photo_id = models.CharField(max_length=8, unique=True, db_index=True)
    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE,
        related_name='photographs', db_index=True)

    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    capture_date = models.DateTimeField(null=True, blank=True, db_index=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    camera = models.CharField(max_length=120, blank=True)
    lens = models.CharField(max_length=120, blank=True)
    focal_length = models.CharField(max_length=32, blank=True)
    aperture = models.CharField(max_length=32, blank=True)
    shutter_speed = models.CharField(max_length=32, blank=True)
    iso = models.PositiveIntegerField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)

    published = models.BooleanField(default=True, db_index=True)
    # null display_order means "fall back to capture date" in the gallery sort
    display_order = models.IntegerField(null=True, blank=True)

    # filled by the ingest pipeline, read-only in admin
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    orientation = models.CharField(
        max_length=10, choices=ORIENTATION_CHOICES, blank=True)
    # bumped on every (re)process so templates can cache-bust the derivatives
    version = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['collection', 'display_order', '-capture_date']

    def __str__(self):
        return self.title or self.photo_id

    @property
    def thumb_url(self):
        return f'{storage.derivative_url(self.photo_id, "thumb")}?v={self.version}'

    @property
    def large_url(self):
        return f'{storage.derivative_url(self.photo_id, "large")}?v={self.version}'


@receiver(post_delete, sender=Photograph)
def _remove_derivatives(sender, instance, **kwargs):
    # covers admin single + bulk deletes and any programmatic delete
    storage.unlink_derivatives(instance.photo_id)
