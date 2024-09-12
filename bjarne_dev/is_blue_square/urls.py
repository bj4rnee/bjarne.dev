from django.urls import path

from . import views

urlpatterns = [
    path('', views.ibs_view, name='is-blue-square'),
]