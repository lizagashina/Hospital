from django.urls import path
from . import views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False)),  # Добавьте эту строку
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('home/', views.home_view, name='home'),
    path('department/<int:department_id>/', views.department_view, name='department'),
    path('patients/', views.patients_view, name='patients'),
    path('patients/add/', views.add_patient_view, name='add_patient'),
    path('patients/<int:patient_id>/', views.patient_detail_view, name='patient_detail'),
    path('admissions/<int:admission_id>/', views.admission_detail_view, name='admission_detail'),
    path('admissions/<int:admission_id>/discharge/', views.discharge_patient_view, name='discharge_patient'),
    path('admissions/add/<int:patient_id>/', views.add_admission_view, name='add_admission'),
]
