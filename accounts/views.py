from .models import Department
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from .forms import CustomUserCreationForm, CustomAuthenticationForm

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
    # Проверяем, что пользователь имеет доступ к этому отделению
    if not request.user.departments.filter(id=department_id).exists():
        return redirect('home')
    return render(request, 'accounts/department.html', {'department': department})