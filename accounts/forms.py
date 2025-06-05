import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Patient, Department, Admission, Hospital


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


class AdmissionCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        hospital = kwargs.pop('hospital', None)
        super().__init__(*args, **kwargs)

        if hospital:
            self.fields['department'].queryset = Department.objects.filter(hospital=hospital)

    class Meta:
        model = Admission
        fields = [
            'severity', 'diagnosis', 'temperature',
            'room_number', 'department', 'notes', 'cardiovascular_system', 'respiratory_system',
            'digestive_system', 'urinary_system', 'nervous_system', 'diagnosis_info',
            'life_info', 'admission_info', 'mind', 'movement', 'constitutions'
        ]
        widgets = {
            'admission_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'discharge_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'cardiovascular_system': forms.Textarea(attrs={'rows': 2}),
            'respiratory_system': forms.Textarea(attrs={'rows': 2}),
            'digestive_system': forms.Textarea(attrs={'rows': 2}),
            'urinary_system': forms.Textarea(attrs={'rows': 2}),
            'nervous_system': forms.Textarea(attrs={'rows': 2}),
            'diagnosis_info': forms.Textarea(attrs={'rows': 10}),
            'life_info': forms.Textarea(attrs={'rows': 20}),
            'admission_info': forms.Textarea(attrs={'rows': 10}),

        }



class PatientCreateForm(forms.ModelForm):
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
        cleaned_snils = re.sub(r'[^\d]', '', snils)

        # Проверка формата при вводе
        if not re.match(r'^\d{3}-\d{3}-\d{3} \d{2}$', snils):
            raise forms.ValidationError('Введите СНИЛС в формате XXX-XXX-XXX XX')

        # Проверка уникальности СНИЛС в больнице
        if self.hospital and Patient.objects.filter(snils=cleaned_snils, hospital=self.hospital).exists():
            raise forms.ValidationError('Пациент с таким СНИЛС уже существует в этой больнице')

        return cleaned_snils

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

    def __init__(self, *args, **kwargs):
        self.hospital = kwargs.pop('hospital', None)
        super().__init__(*args, **kwargs)

        # Для редактирования делаем СНИЛС необязательным
        if self.instance.pk:
            self.fields['snils'].required = False