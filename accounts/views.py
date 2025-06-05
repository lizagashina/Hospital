import re

import requests
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.utils import timezone
from django.db.models import Max
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .forms import CustomUserCreationForm, CustomAuthenticationForm, PatientCreateForm, AdmissionCreateForm
from .models import Patient, Department, Admission


# Декоратор для проверки принадлежности к больнице
def hospital_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.hospital:
            return render(request, 'accounts/waiting_approval.html')
        return view_func(request, *args, **kwargs)

    return wrapper


@login_required
def mkb10_search_view(request):
    if not settings.GIGDATA_API_KEY:
        raise ValueError("API key not configured")
    if request.method == 'POST':
        query = request.POST.get('query', '')

        headers = {
            'Authorization': settings.GIGDATA_API_KEY,
            'Accept': 'application/json'
        }

        payload = {
            "query": query,
            "count": 100
        }

        try:
            response = requests.post(
                'https://api.gigdata.ru/api/v2/suggest/mkb',
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return JsonResponse(data)
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': str(e)}, status=500)

    return render(request, 'accounts/mkb10_search.html')


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='accounts.backends.EmployeeNumberOrUsernameBackend')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@hospital_required
def home_view(request):
    # Только отделения текущей больницы
    departments = Department.objects.filter(hospital=request.user.hospital)
    context = {
        'departments': departments,  # или user_departments
        'hospital': request.user.hospital
    }
    return render(request, 'accounts/home.html', context)


@login_required
@hospital_required
def department_view(request, department_id):
    department = get_object_or_404(
        Department,
        id=department_id,
        hospital=request.user.hospital
    )
    patients = department.get_current_patients()
    # Проверяем, что пользователь имеет доступ к этому отделению
    if not request.user.departments.filter(id=department_id).exists():
        return redirect('home')
    patients = department.get_current_patients()
    return render(request, 'accounts/department.html', {
        'department': department,
        'patients': patients
    })


@login_required
@hospital_required
def patients_view(request):
    # Фильтрация пациентов по больнице
    patients = Patient.objects.filter(hospital=request.user.hospital).annotate(
        last_admission_date=Max('admissions__admission_date')
    ).order_by('-last_admission_date')

    search_performed = False

    if request.method == 'GET' and any(
            param in request.GET for param in ['last_name', 'first_name', 'middle_name', 'snils', 'birth_date']):
        search_performed = True
        search_query = {}

        if last_name := request.GET.get('last_name'):
            search_query['last_name__icontains'] = last_name
        if first_name := request.GET.get('first_name'):
            search_query['first_name__icontains'] = first_name
        if middle_name := request.GET.get('middle_name'):
            search_query['middle_name__icontains'] = middle_name
        if snils := request.GET.get('snils'):
            search_query['snils__icontains'] = snils.replace('-', '').replace(' ', '')
        if birth_date := request.GET.get('birth_date'):
            search_query['birth_date'] = birth_date

        if search_query:
            patients = patients.filter(**search_query)

    return render(request, 'accounts/patients.html', {
        'patients': patients,
        'search_params': request.GET,
        'search_performed': search_performed
    })


@login_required
@hospital_required
def add_patient_view(request):
    if request.method == 'POST':
        patient_form = PatientCreateForm(request.POST, hospital=request.user.hospital)
        if patient_form.is_valid():
            patient = patient_form.save(commit=False)
            patient.hospital = request.user.hospital  # Привязываем к больнице
            patient.save()
            return redirect('add_admission', patient_id=patient.id)
    else:
        patient_form = PatientCreateForm(hospital=request.user.hospital)

    # Передаем больницу в форму для валидации СНИЛС
    patient_form.hospital = request.user.hospital
    return render(request, 'accounts/add_patient.html', {'patient_form': patient_form})


@login_required
@hospital_required
def add_admission_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, hospital=request.user.hospital)

    if request.method == 'POST':
        admission_form = AdmissionCreateForm(request.POST, hospital=request.user.hospital)
        if admission_form.is_valid():
            admission = admission_form.save(commit=False)
            admission.patient = patient
            admission.save()
            return redirect('patient_detail', patient_id=patient.id)
    else:
        admission_form = AdmissionCreateForm(hospital=request.user.hospital)

    return render(request, 'accounts/add_admission.html', {
        'admission_form': admission_form,
        'patient': patient,
        'is_existing_patient': True  # Флаг для изменения заголовка
    })


@login_required
@hospital_required
def patient_detail_view(request, patient_id):
    patient = get_object_or_404(
        Patient,
        id=patient_id,
        hospital=request.user.hospital
    )
    active_admission = patient.admissions.filter(discharge_date__isnull=True).first()
    past_admissions = patient.admissions.filter(discharge_date__isnull=False).order_by('-admission_date')

    return render(request, 'accounts/patient_detail.html', {
        'patient': patient,
        'active_admission': active_admission,
        'past_admissions': past_admissions
    })


@login_required
@hospital_required
def patient_detail_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, hospital=request.user.hospital)
    active_admission = patient.admissions.filter(
        discharge_date__isnull=True,
        department__hospital=request.user.hospital
    ).first()
    past_admissions = patient.admissions.filter(
        discharge_date__isnull=False,
        department__hospital=request.user.hospital
    ).order_by('-admission_date')

    patient_form = PatientCreateForm(instance=patient, hospital=request.user.hospital)

    return render(request, 'accounts/patient_detail.html', {
        'patient': patient,
        'active_admission': active_admission,
        'past_admissions': past_admissions,
        'patient_form': patient_form  # Добавляем форму в контекст
    })


@login_required
@hospital_required
def admission_detail_view(request, admission_id):
    admission = get_object_or_404(
        Admission,
        id=admission_id,
        patient__hospital=request.user.hospital
    )
    return render(request, 'accounts/admission_detail.html', {
        'admission': admission
    })


@login_required
@hospital_required
def discharge_patient_view(request, admission_id):
    admission = get_object_or_404(
        Admission,
        id=admission_id,
        discharge_date__isnull=True,
        patient__hospital=request.user.hospital
    )

    if request.method == 'POST':
        admission.discharge_date = timezone.now()
        admission.save()
        return redirect('patient_detail', patient_id=admission.patient.id)

    return redirect('admission_detail', admission_id=admission_id)


@login_required
@hospital_required
def edit_patient_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, hospital=request.user.hospital)

    if request.method == 'POST':
        # Обработка данных формы
        data = request.POST.copy()
        # Очищаем СНИЛС от форматирования перед сохранением
        if 'snils' in data:
            data['snils'] = re.sub(r'[^\d]', '', data['snils'])

        patient.last_name = data.get('last_name', patient.last_name)
        patient.first_name = data.get('first_name', patient.first_name)
        patient.middle_name = data.get('middle_name', patient.middle_name)
        patient.birth_date = data.get('birth_date', patient.birth_date)
        patient.gender = data.get('gender', patient.gender)
        patient.snils = data.get('snils', patient.snils)
        patient.height = data.get('height', patient.height)
        patient.weight = data.get('weight', patient.weight)
        patient.birth_place = data.get('birth_place', patient.birth_place)

        try:
            patient.full_clean()  # Валидация модели
            patient.save()
            return redirect('patient_detail', patient_id=patient.id)
        except ValidationError as e:
            # Обработка ошибок валидации
            pass

    # Получаем текущие данные о поступлениях для контекста
    active_admission = patient.admissions.filter(discharge_date__isnull=True).first()
    past_admissions = patient.admissions.filter(discharge_date__isnull=False).order_by('-admission_date')

    return render(request, 'accounts/patient_detail.html', {
        'patient': patient,
        'active_admission': active_admission,
        'past_admissions': past_admissions
    })
