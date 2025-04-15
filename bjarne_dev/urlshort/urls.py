from django.urls import path

from . import views

urlpatterns = [
    path('', views.url_short_view, name='urlshort'),
    path('<str:url_hash>', views.redirect_hash, name='redirect_hash'),
]