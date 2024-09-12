from django.urls import path

from . import views

urlpatterns = [
    path('', views.synthwave_view, name='synthwave'),
]