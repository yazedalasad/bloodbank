from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'), 
    path('donors/', views.donor_list, name='donor_list'),
    path('donors/new/', views.donor_create, name='donor_create'),
    path('donations/new/', views.donation_create, name='donation_create'),
    path('requests/new/', views.request_blood, name='request_blood'),
    path('inventory/', views.inventory_report, name='inventory_report'),
    path('emergency/', views.emergency_request, name='emergency_request'),
    path('emergency/stats/', views.get_emergency_stats, name='emergency_stats'),
    path('register/doctor/', views.register_doctor, name='register_doctor'),
    path('register/patient/', views.register_patient, name='register_patient'),
    path('login/', views.login_view, name='login'),
    path('accounts/login/', views.login_view, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('reports/doctor/',views.generate_doctor_report, name='doctor_report'),
    path('reports/patient/', views.generate_patient_report, name='patient_report'),


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
