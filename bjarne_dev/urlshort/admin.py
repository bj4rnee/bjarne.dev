from django.contrib import admin
from .models import Shorted_url


class UrlshortAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_url', 'hash', 'creation_date')
    list_filter = (['creation_date'])
    search_fields = ('original_url', 'hash')

admin.site.register(Shorted_url, UrlshortAdmin)