from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='service_worker'),
    path('offline/', views.offline_view, name='offline'),
    path('robots.txt', views.robots_txt_view, name='robots_txt'),
]

