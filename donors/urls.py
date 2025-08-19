from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'), 
    path('donors/', views.donor_list, name='donor_list'),
    path('donors/new/', views.donor_create, name='donor_create'),
    path('donations/new/', views.donation_create, name='donation_create'),
    path('requests/new/', views.request_blood, name='request_blood'),
    path('inventory/', views.inventory_report, name='inventory_report'),


]
