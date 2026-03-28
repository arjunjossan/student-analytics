from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reset/', views.reset_data, name='reset'),
    path('delete/<int:file_id>/', views.delete_file, name='delete_file'),
    path('set-active/<int:file_id>/', views.set_active, name='set_active'),
]