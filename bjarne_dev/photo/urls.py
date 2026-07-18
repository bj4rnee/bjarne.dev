from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='photo_index'),
    path('<slug:slug>/', views.collection, name='photo_collection'),
]
