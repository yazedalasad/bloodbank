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
    path('emergency/locator/', views.emergency_donor_locator, name='emergency_locator'),
    path('emergency/mass-alert/', views.mass_emergency_alert, name='mass_emergency_alert'),
    path('emergency/quick/<str:blood_type>/', views.quick_emergency_alert, name='quick_emergency'),
    path('emergency/quick/<str:blood_type>/<str:emergency_type>/', views.quick_emergency_alert, name='quick_emergency_type'),
    path('emergency/check-capacity/', views.check_email_capacity, name='check_email_capacity'),
    path('predictor/shortage/', views.blood_shortage_predictor, name='shortage_predictor'),
    path('donors/availability/', views.donor_availability_calendar, name='availability_calendar'),
    path('matching/smart/', views.smart_donor_matching, name='smart_matching'),
    path('matching/smart/<int:request_id>/', views.smart_donor_matching, name='smart_matching_request'),
    path('check-availability/', views.check_donor_availability, name='check_availability'),
    # Location management URLs
    path('location/add/', views.add_user_location, name='add_user_location'),
    path('location/map/', views.user_location_map, name='user_location_map'),
    path('location/update/', views.update_user_location, name='update_user_location'),
    path('location/info/', views.get_user_location_info, name='get_user_location_info'),
    path('location/emergency-prepare/', views.location_based_emergency_prepare, name='location_based_emergency_prepare'),
    
    # AJAX endpoints
    path('locations/search/', views.search_locations, name='search_locations'),
    path('locations/<int:location_id>/details/', views.get_location_details, name='get_location_details'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
