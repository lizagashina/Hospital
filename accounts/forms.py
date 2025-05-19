import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Patient, Department, Admission


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


class AdmissionForm(forms.ModelForm):
    class Meta:
        model = Admission
        fields = ['severity', 'diagnosis', 'temperature', 'room_number', 'department', 'notes']
        widgets = {
            'admission_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'discharge_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }


class PatientForm(forms.ModelForm):
    snils = forms.CharField(
        max_length=14,
        label='СНИЛС',
        help_text='Формат: XXX-XXX-XXX XX',
        widget=forms.TextInput(attrs={'placeholder': '123-456-789 01'})
    )
    gender = forms.ChoiceField(
        choices=Patient.GENDER_CHOICES,
        label='Пол',
        widget=forms.RadioSelect
    )

    def clean_snils(self):
        snils = self.cleaned_data.get('snils', '')
        # Проверка формата при вводе
        if not re.match(r'^\d{3}-\d{3}-\d{3} \d{2}$', snils):
            raise forms.ValidationError('Введите СНИЛС в формате XXX-XXX-XXX XX')
        return re.sub(r'[^\d]', '', snils)

    class Meta:
        model = Patient
        fields = [
            'last_name', 'first_name', 'middle_name', 'gender',
            'birth_date', 'birth_place', 'snils',
            'height', 'weight'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }