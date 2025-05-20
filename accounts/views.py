import requests
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.utils import timezone
from django.db.models import Max
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .forms import CustomUserCreationForm, CustomAuthenticationForm, PatientCreateForm, AdmissionCreateForm
from .models import Patient, Department, Admission





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
def home_view(request):
    user_departments = request.user.departments.all()
    return render(request, 'accounts/home.html', {'departments': user_departments})


@login_required
def department_view(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    patients = department.get_current_patients()
    # Проверяем, что пользователь имеет доступ к этому отделению
    if not request.user.departments.filter(id=department_id).exists():
        return redirect('home')
    return render(request, 'accounts/department.html', {
        'department': department,
        'patients': patients
    })


@login_required
def patients_view(request):
    patients = Patient.objects.annotate(
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
def add_patient_view(request):
    if request.method == 'POST':
        patient_form = PatientCreateForm(request.POST)
        if patient_form.is_valid():
            patient = patient_form.save()
            return redirect('add_admission', patient_id=patient.id)
    else:
        patient_form = PatientCreateForm()

    return render(request, 'accounts/add_patient.html', {'patient_form': patient_form})


@login_required
def add_admission_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        admission_form = AdmissionCreateForm(request.POST)
        if admission_form.is_valid():
            admission = admission_form.save(commit=False)
            admission.patient = patient
            admission.save()
            return redirect('patient_detail', patient_id=patient.id)
    else:
        admission_form = AdmissionCreateForm()

    return render(request, 'accounts/add_admission.html', {
        'admission_form': admission_form,
        'patient': patient,
        'is_existing_patient': True  # Флаг для изменения заголовка
    })


@login_required
def patient_detail_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    active_admission = patient.admissions.filter(discharge_date__isnull=True).first()
    past_admissions = patient.admissions.filter(discharge_date__isnull=False).order_by('-admission_date')

    return render(request, 'accounts/patient_detail.html', {
        'patient': patient,
        'active_admission': active_admission,
        'past_admissions': past_admissions
    })


@login_required
def admission_detail_view(request, admission_id):
    admission = get_object_or_404(Admission, id=admission_id)
    return render(request, 'accounts/admission_detail.html', {'admission': admission})


@login_required
def discharge_patient_view(request, admission_id):
    admission = get_object_or_404(Admission, id=admission_id, discharge_date__isnull=True)
    if request.method == 'POST':
        admission.discharge_date = timezone.now()
        admission.save()
        return redirect('patient_detail', patient_id=admission.patient.id)
    return redirect('admission_detail', admission_id=admission_id)
