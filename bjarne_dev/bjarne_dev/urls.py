"""
URL configuration for bjarne_dev project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include

from .sitemaps import StaticViewSitemap
from photo.sitemaps import PhotoSitemap

# hack to get case insensitive urlpatterns to work
import re
from functools import partial

from django.urls.resolvers import RoutePattern, RegexPattern, _route_to_regex
from django.urls.conf import _path
from django.core.exceptions import ImproperlyConfigured


# ipath hack overrides RoutePattern._compile, which Django 6.0 removed (routing moved to a descriptor). ipath silently lost its case-insensitivity. re_ipath still works
class IRoutePattern(RoutePattern):
    def _compile(self, route):
        return re.compile(_route_to_regex(route, self._is_endpoint)[0], re.IGNORECASE)


class IRegexPattern(RegexPattern):
    def _compile(self, regex):
        """Compile and return the given regular expression."""
        try:
            return re.compile(regex, re.IGNORECASE)
        except re.error as e:
            raise ImproperlyConfigured(
                '"%s" is not a valid regular expression: %s' % (regex, e)
            ) from e


# use these if the url should be case insensitive
ipath = partial(_path, Pattern=IRoutePattern)
re_ipath = partial(_path, Pattern=IRegexPattern)

sitemaps = {
    'static': StaticViewSitemap,
    'photo': PhotoSitemap,
}

urlpatterns = [
    path('', include('index.urls')),
    path('admin/', admin.site.urls),
    path('synthwave/', include('synthwave.urls')),
    path('bcrash/', include('bcrash.urls')),
    path('is-blue-square/', include('is_blue_square.urls')),
    path('s/', include('urlshort.urls')),
    #path('f/', include('filelink.urls')),
    path('photo/', include('photo.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    # static pattern for local dev environment (to test /photo/ serving)
    urlpatterns += static(settings.PHOTO_STORAGE_URL,
                          document_root=settings.PHOTO_STORAGE_DIR)