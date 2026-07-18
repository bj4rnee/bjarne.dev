"""
Site-wide sitemap. Lists the public, indexable landing pages only.

The sitemap deliberately spans apps (the URL names below are defined in
six different app urls.py modules), so it lives in the project package
next to urls.py rather than inside any single app. User-generated and
sensitive routes are intentionally excluded: urlshort redirects, FileLink
view/blob pages, the admin, and POST-only endpoints. The domain comes
from the request host (no django.contrib.sites), protocol is pinned to
https.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    protocol = "https"

    def items(self):
        return [
            "index",
            "synthwave",
            "bcrash",
            "is-blue-square",
            "urlshort",
            #"filelink",
            "photo_index",
        ]

    def location(self, item):
        return reverse(item)
