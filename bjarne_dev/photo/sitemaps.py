"""
Dynamic sitemap for the photography collections. The static landing page
(photo_index) is listed by the project-level StaticViewSitemap.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Collection


class PhotoSitemap(Sitemap):
    protocol = 'https'

    def items(self):
        return list(Collection.objects.all())

    def location(self, obj):
        return reverse('photo_collection', args=[obj.slug])
