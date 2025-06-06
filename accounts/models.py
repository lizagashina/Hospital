import re

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.contrib.auth.models import BaseUserManager
from transliterate import translit


class CustomUserManager(BaseUserManager):
    def create_superuser(self, employee_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Генерируем username, если не предоставлен
        if 'username' not in extra_fields:
            full_name = extra_fields.get('full_name', '')
            first_two_words = ' '.join(full_name.split()[:2])
            extra_fields['username'] = slugify(first_two_words.replace(' ', '_').lower())

        return self._create_user(employee_number, password, **extra_fields)

    def _create_user(self, employee_number, password, **extra_fields):
        if not employee_number:
            raise ValueError('The Employee Number must be set')
        user = self.model(employee_number=employee_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class Hospital(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название больницы')
    address = models.TextField(verbose_name='Адрес')

    def __str__(self):
        return self.name


class Department(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        verbose_name='Больница',
        related_name='hospital_departments'
    )
    name = models.CharField(max_length=100, verbose_name='Название отделения')
    code = models.CharField(max_length=10, unique=True, verbose_name='Код отделения')
    description = models.TextField(blank=True, verbose_name='Описание')

    def get_current_patients(self):
        return Patient.objects.filter(
            admissions__department=self,
            admissions__discharge_date__isnull=True,
            hospital=self.hospital  # Добавляем фильтр по больнице
        ).distinct()

    class Meta:
        ordering = ['hospital', 'name']  # Правильный ordering

    def __str__(self):
        return f"{self.name} ({self.code})"


class CustomUser(AbstractUser):
    objects = CustomUserManager()
    full_name = models.CharField(max_length=100, verbose_name='ФИО')
    position = models.CharField(max_length=100, verbose_name='Должность')
    departments = models.ManyToManyField(Department, blank=True, verbose_name='Отделения')
    employee_number = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Номер сотрудника',
        validators=[RegexValidator(r'^\d{1,10}$', 'Номер сотрудника должен содержать только цифры')]
    )
    phone_number = models.CharField(
        max_length=15,
        verbose_name='Номер телефона',
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Введите корректный номер телефона')]
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Больница',
        related_name='employees'
    )

    # Убираем username из обязательных полей
    USERNAME_FIELD = 'employee_number'
    REQUIRED_FIELDS = ['full_name', 'position', 'phone_number']

    def save(self, *args, **kwargs):
        if not self.username and self.full_name:
            name_parts = self.full_name.split()
            if len(name_parts) >= 2:
                first_part = name_parts[0]
                second_part = name_parts[1]
                try:
                    # Пробуем транслитерировать
                    first_en = translit(first_part, 'ru', reversed=True)
                    second_en = translit(second_part, 'ru', reversed=True)
                    base_username = f"{first_en}_{second_en}"
                except:
                    # Если transliterate не установлен или ошибка
                    base_username = f"{name_parts[0]}_{name_parts[1]}"
            else:
                base_username = name_parts[0] if name_parts else 'user'

            # Очистка и приведение к нижнему регистру
            self.username = re.sub(r'[^a-z0-9_]', '', base_username.lower())

            # Уникальность username
            original = self.username
            counter = 1
            while CustomUser.objects.filter(username=self.username).exclude(pk=self.pk).exists():
                self.username = f"{original}_{counter}"
                counter += 1

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['hospital', 'full_name']  # Правильный ordering

    def __str__(self):
        return f"{self.full_name} ({self.employee_number})"


class Patient(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        verbose_name='Больница',
        related_name='patients'
    )
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

    @property
    def has_active_admission(self):
        return self.admissions.filter(discharge_date__isnull=True).exists()

    height = models.PositiveSmallIntegerField(verbose_name='Рост (см)')
    weight = models.PositiveSmallIntegerField(verbose_name='Вес (кг)')

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['snils', 'hospital'],
                name='unique_snils_per_hospital'
            )
        ]


class Admission(models.Model):
    MIND_CHOICES = [
        ('clear', 'Ясное'),
        ('confused', 'Спутанное'),
        ('soporose', 'Сопорозное'),
        ('comatose', 'Коматозное'),
    ]
    SEVERITY_CHOICES = [
        ('mild', 'Удовлетворительное'),
        ('moderate', 'Средней тяжести'),
        ('severe', 'Тяжёлое'),
    ]
    MOVEMENT_CHOICES = [
        ('active', 'Активное'),
        ('passive', 'Пассивное'),
        ('other', 'Вынужденное с его особенностями'),
    ]
    CONSTITUTION_CHOICES = [
        ('normal', 'Нормостеник'),
        ('astenic', 'Астеник'),
        ('giper', 'Гиперстеник'),
    ]

    DEFAULT_DIAGNOSIS_INFO = (
        "Начало болезни: когда и как началось заболевание.\n\n"
        "Состояние больного непосредственно перед заболеванием: предполагаемая причина заболевания.\n\n"
        "Результаты проведенных ранее исследований: \n\n"
        "Способы лечения, применявшиеся до поступления в клинику, в т.ч. на амбулаторном этапе: \n\n"
        "Непосредственные причины данной госпитализации: \n\n"
    )

    DEFAULT_LIFE_INFO = (
        "Образование и профессиональный анамнез: \n\n"
        "Жилищные условия: \n\n"
        "Перенесенные заболевания: \n\n"
        "Привычные интоксикации: \n\n"
        "Гинекологический анамнез: \n\n"
        "Наследственность: \n\n"
        "Семейная жизнь: \n\n"
        "Эпидемиологический анамнез: \n\n"
        "Страховой анамнез: \n\n"
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='admissions')
    admission_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата поступления')
    discharge_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата выписки')
    severity = models.CharField(max_length=10, blank=True, choices=SEVERITY_CHOICES, verbose_name='Состояние')
    mind = models.CharField(max_length=10, blank=True, choices=MIND_CHOICES, verbose_name='Сознание')
    movement = models.CharField(max_length=10, blank=True, choices=MOVEMENT_CHOICES, verbose_name='Положение')
    constitutions = models.CharField(max_length=10, blank=True, choices=CONSTITUTION_CHOICES,
                                     verbose_name='Тип конституции')
    diagnosis = models.TextField(verbose_name='Диагноз')
    temperature = models.DecimalField(max_digits=3, blank=True, null=True, decimal_places=1, verbose_name='Температура')
    adhd = models.CharField(max_length=10, blank=True, verbose_name='Артериальное давление')
    heart_rate = models.CharField(max_length=10, blank=True, verbose_name='ЧСС')
    room_number = models.CharField(max_length=10, verbose_name='Номер палаты')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='Отделение')
    diagnosis_info = models.TextField(
        verbose_name='Анамнез заболевания',
        default=DEFAULT_DIAGNOSIS_INFO,
        blank=True
    )
    life_info = models.TextField(
        verbose_name='Анамнез жизни',
        default=DEFAULT_LIFE_INFO,
        blank=True
    )
    admission_info = models.TextField(
        verbose_name='Данные объективного исследования больного',
        default=DEFAULT_DIAGNOSIS_INFO,
        blank=True
    )
    cardiovascular_system = models.TextField(
        verbose_name='Сердечно-сосудистая система',
        default='Нет',
        blank=True
    )
    respiratory_system = models.TextField(
        verbose_name='Дыхательная система',
        default='Нет',
        blank=True
    )
    digestive_system = models.TextField(
        verbose_name='Система пищеварения',
        default='Нет',
        blank=True
    )
    urinary_system = models.TextField(
        verbose_name='Мочевыделительная система',
        default='Нет',
        blank=True
    )
    nervous_system = models.TextField(
        verbose_name='Нервная система',
        default='Нет',
        blank=True
    )
    notes = models.TextField(blank=True, verbose_name='Иные записи о состоянии здоровья')

    @property
    def is_active(self):
        return self.discharge_date is None

    class Meta:
        ordering = ['-admission_date']

    def __str__(self):
        return f"{self.patient} - {self.admission_date.date()}"


class HealthNote(models.Model):
    NOTE_TYPE_CHOICES = [
        ('prescription', 'Назначение'),
        ('research', 'Исследование'),
        ('info', 'Запись состояния пациента'),
        ('note', 'Запись истории болезни'),
    ]

    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='entry_notes')
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES)
    text = models.TextField(blank=True, null=True)
    valueHigh = models.CharField(max_length=3, blank=True, null=True)
    valueLow = models.CharField(max_length=3, blank=True, null=True)
    hr_value = models.PositiveIntegerField(blank=True, null=True)
    temperature_value = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

