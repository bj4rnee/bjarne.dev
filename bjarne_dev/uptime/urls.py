from django.urls import path

from . import views

urlpatterns = [
    path('', views.uptime_view, name='uptime'),
]