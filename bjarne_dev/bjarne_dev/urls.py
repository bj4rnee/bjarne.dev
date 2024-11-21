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
from django.contrib import admin
from django.urls import path, include

# hack to get case insensitive urlpatterns to work
import re
from functools import partial

from django.urls.resolvers import RoutePattern, RegexPattern, _route_to_regex
from django.urls.conf import _path
from django.core.exceptions import ImproperlyConfigured


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

urlpatterns = [
    path('', include('index.urls')),
    path('admin/', admin.site.urls),
    path('cert/', include('cert.urls')),
    path('synthwave/', include('synthwave.urls')),
    path('bcrash/', include('bcrash.urls')),
    path('uptime/', include('uptime.urls')),
    path('is-blue-square/', include('is_blue_square.urls')),
]