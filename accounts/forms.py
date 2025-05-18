from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


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