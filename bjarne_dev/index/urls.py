from django.urls import path

from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('incr-visit/', views.track_visit, name='track_visit'),
    path('ip/', views.ip_view, name='ip'),
    path('ip/ping', views.ip_ping, name='ip_ping'),
    path('ip/rdns', views.ip_rdns, name='ip_rdns'),
    path('display/', views.display_view, name='display'),
]