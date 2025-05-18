import re

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.text import slugify


class Department(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название отделения')
    code = models.CharField(max_length=10, unique=True, verbose_name='Код отделения')
    description = models.TextField(blank=True, verbose_name='Описание')

    def __str__(self):
        return f"{self.name} ({self.code})"

class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=100, verbose_name='ФИО')
    position = models.CharField(max_length=100, verbose_name='Должность')
    departments = models.ManyToManyField(Department, blank=True, verbose_name='Отделения')
    employee_number = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Номер сотрудника',
        validators=[RegexValidator(r'^\d{1,10}$', 'Номер сотрудника должен содержать только цифры')]
    )
    phone_number = models.CharField(
        max_length=15,
        verbose_name='Номер телефона',
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Введите корректный номер телефона')]
    )

    # Убираем username из обязательных полей
    USERNAME_FIELD = 'employee_number'
    REQUIRED_FIELDS = ['full_name', 'position', 'phone_number']

    def save(self, *args, **kwargs):
        # Генерируем username из первых двух слов ФИО
        if not self.username:
            first_two_words = ' '.join(self.full_name.split()[:2])
            self.username = slugify(first_two_words.replace(' ', '_').lower())

        # Убедимся, что username уникален
        counter = 1
        original_username = self.username
        while CustomUser.objects.filter(username=self.username).exclude(pk=self.pk).exists():
            self.username = f"{original_username}_{counter}"
            counter += 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.employee_number})"



class Patient(models.Model):
    SEVERITY_CHOICES = [
        ('mild', 'Удовлетворительное'),
        ('moderate', 'Средней тяжести'),
        ('severe', 'Тяжёлое'),
    ]
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    # Основные данные
    last_name = models.CharField(max_length=50, verbose_name='Фамилия')
    first_name = models.CharField(max_length=50, verbose_name='Имя')
    middle_name = models.CharField(max_length=50, blank=True, verbose_name='Отчество')
    birth_date = models.DateField(verbose_name='Дата рождения')
    birth_place = models.CharField(max_length=100, blank=True, verbose_name='Место рождения')
    snils = models.CharField(
        max_length=14,
        unique=True,
        verbose_name='СНИЛС',
        help_text='Формат: XXX-XXX-XXX XX'
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        verbose_name='Пол'
    )

    def clean(self):
        super().clean()
        # Очищаем СНИЛС от всех символов, кроме цифр
        if self.snils:
            cleaned_snils = re.sub(r'[^\d]', '', self.snils)
            if len(cleaned_snils) != 11:
                raise ValidationError({'snils': 'СНИЛС должен содержать 11 цифр'})
            self.snils = cleaned_snils

    def formatted_snils(self):
        """Метод для отображения СНИЛС в стандартном формате"""
        if len(self.snils) == 11:
            return f"{self.snils[:3]}-{self.snils[3:6]}-{self.snils[6:9]} {self.snils[9:]}"
        return self.snils


    height = models.PositiveSmallIntegerField(verbose_name='Рост (см)')
    weight = models.PositiveSmallIntegerField(verbose_name='Вес (кг)')

    # Данные поступления
    admission_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата поступления')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, verbose_name='Состояние')
    diagnosis = models.TextField(verbose_name='Диагноз')
    temperature = models.DecimalField(max_digits=3, decimal_places=1, verbose_name='Температура')
    room_number = models.CharField(max_length=10, verbose_name='Номер палаты')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='Отделение')
    discharged = models.BooleanField(default=False, verbose_name='Выписан')
    discharge_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата выписки')

    def status_display(self):
        return "Выписан" if self.discharged else "В стационаре"

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}"