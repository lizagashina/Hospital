from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Patient, Department


class CustomUserCreationForm(UserCreationForm):
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ('full_name', 'position', 'employee_number', 'phone_number', 'password1', 'password2')
        widgets = {
            'full_name': forms.TextInput(attrs={'autofocus': True}),
        }

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Номер сотрудника или логин',
        widget=forms.TextInput(attrs={'autofocus': True})
    )


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'last_name', 'first_name', 'middle_name',
            'birth_date', 'birth_place', 'snils',
            'height', 'weight', 'severity',
            'diagnosis', 'temperature', 'room_number',
            'department'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }