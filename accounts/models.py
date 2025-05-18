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