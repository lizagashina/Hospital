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
from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token
from django.template import RequestContext

from .forms import CustomUserCreationForm, CustomAuthenticationForm, PatientCreateForm, AdmissionCreateForm
from .models import Patient, Department, Admission, HealthNote


@requires_csrf_token
def custom_404_view(request, exception):
    return render(request, '404.html', status=404)


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
    departments = Department.objects.filter(hospital=request.user.hospital)
    context = {
        'departments': departments,
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
            patient.hospital = request.user.hospital
            patient.save()
            return redirect('add_admission', patient_id=patient.id)
    else:
        patient_form = PatientCreateForm(hospital=request.user.hospital)

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
        'is_existing_patient': True
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
        'patient_form': patient_form
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
        data = request.POST.copy()
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
            pass

    active_admission = patient.admissions.filter(discharge_date__isnull=True).first()
    past_admissions = patient.admissions.filter(discharge_date__isnull=False).order_by('-admission_date')

    return render(request, 'accounts/patient_detail.html', {
        'patient': patient,
        'active_admission': active_admission,
        'past_admissions': past_admissions
    })


@login_required
@hospital_required
def notes_view(request, admission_id):
    admission = get_object_or_404(Admission, id=admission_id, patient__hospital=request.user.hospital)
    notes = admission.entry_notes.all().order_by('-created_at')
    return render(request, 'accounts/notes.html', {
        'admission': admission,
        'notes': notes
    })


@login_required
@hospital_required
def add_note_view(request, admission_id):
    admission = get_object_or_404(Admission, id=admission_id, patient__hospital=request.user.hospital)

    if request.method == 'POST':
        note_type = request.POST.get('note_type')
        text = request.POST.get('text')
        value_high = request.POST.get('valueHigh') or None
        value_low = request.POST.get('valueLow') or None
        hr_value = request.POST.get('hr_value') or None
        temperature_value = request.POST.get('temperature_value') or None

        try:
            hr_value = int(hr_value) if hr_value else None
        except ValueError:
            hr_value = None

        try:
            temperature_value = float(temperature_value) if temperature_value else None
        except ValueError:
            temperature_value = None

        HealthNote.objects.create(
            admission=admission,
            note_type=note_type,
            text=text,
            valueHigh=value_high,
            valueLow=value_low,
            hr_value=hr_value,
            temperature_value=temperature_value
        )

        return redirect('notes', admission_id=admission.id)

    return render(request, 'accounts/add_note.html', {
        'admission': admission
    })


@login_required
@hospital_required
def notes_view(request, admission_id):
    admission = get_object_or_404(Admission, id=admission_id, patient__hospital=request.user.hospital)
    notes = admission.entry_notes.order_by('-created_at')  # Получаем записи, связанные с поступлением

    return render(request, 'accounts/notes.html', {
        'admission': admission,
        'notes': notes
    })


@login_required
@hospital_required
def note_detail_view(request, note_id):
    note = get_object_or_404(HealthNote, id=note_id, admission__patient__hospital=request.user.hospital)
    return render(request, 'accounts/note_detail.html', {
        'note': note
    })


from django.shortcuts import render, get_object_or_404


def analytics_view(request, admission_id):
    admission = get_object_or_404(Admission, id=admission_id)
    metric = request.GET.get('metric', 'hr')  # по умолчанию ЧСС

    if metric == 'temp':
        data_points = HealthNote.objects.filter(admission=admission).exclude(temperature_value__isnull=True).order_by(
            'created_at')
        labels = [note.created_at.strftime("%d.%m %H:%M") for note in data_points]
        values = [float(note.temperature_value) for note in data_points]
        context = {
            'labels': labels,
            'values': values,
            'metric': metric,
            'admission': admission
        }
    elif metric == 'bp':
        data_points = HealthNote.objects.filter(admission=admission).filter(valueHigh__isnull=False,
                                                                            valueLow__isnull=False).order_by(
            'created_at')
        labels = [note.created_at.strftime("%d.%m %H:%M") for note in data_points]
        value_high = [int(note.valueHigh) for note in data_points]
        value_low = [int(note.valueLow) for note in data_points]
        context = {
            'labels': labels,
            'value_high': value_high,
            'value_low': value_low,
            'metric': metric,
            'admission': admission
        }
    else:
        data_points = HealthNote.objects.filter(admission=admission).exclude(hr_value__isnull=True).order_by(
            'created_at')
        labels = [note.created_at.strftime("%d.%m %H:%M") for note in data_points]
        values = [note.hr_value for note in data_points]
        context = {
            'labels': labels,
            'values': values,
            'metric': metric,
            'admission': admission
        }

    return render(request, 'accounts/analytics.html', context)
