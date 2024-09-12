from django.urls import path

from . import views

urlpatterns = [
    path('', views.cert_view, name='cert'),
]