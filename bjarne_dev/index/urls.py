from django.urls import path

from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('incr-visit/', views.track_visit, name='track_visit'),
]