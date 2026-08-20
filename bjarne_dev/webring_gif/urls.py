from django.urls import path

from . import views

urlpatterns = [
    path('', views.webring_gif, name='webring_gif'),
]
