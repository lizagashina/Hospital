from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Department, Patient, Admission, Hospital


class CustomUserDepartmentForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Фильтруем отделения только для текущей больницы пользователя
        if 'departments' in self.fields:
            if self.instance and self.instance.hospital:
                self.fields['departments'].queryset = Department.objects.filter(
                    hospital=self.instance.hospital
                )
            else:
                self.fields['departments'].queryset = Department.objects.none()


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'address')
    search_fields = ('name', 'address')
    ordering = ('name',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'get_hospital')
    list_filter = ('hospital',)
    search_fields = ('name', 'code', 'hospital__name')
    ordering = ('hospital', 'name')

    def get_hospital(self, obj):
        return obj.hospital.name if obj.hospital else '-'

    get_hospital.short_description = 'Больница'
    get_hospital.admin_order_field = 'hospital'


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'last_name',
        'first_name',
        'get_hospital',
        'get_current_department',
        'get_current_room',
        'get_status',
        'snils',
        'birth_date'
    )
    list_filter = ('gender', 'hospital')
    search_fields = ('last_name', 'first_name', 'middle_name', 'snils', 'hospital__name')
    ordering = ('hospital', 'last_name', 'first_name')

    def get_hospital(self, obj):
        return obj.hospital.name if obj.hospital else '-'

    get_hospital.short_description = 'Больница'
    get_hospital.admin_order_field = 'hospital'

    def get_current_department(self, obj):
        admission = obj.admissions.filter(discharge_date__isnull=True).first()
        return admission.department.name if admission else '-'

    get_current_department.short_description = 'Отделение'

    def get_current_room(self, obj):
        admission = obj.admissions.filter(discharge_date__isnull=True).first()
        return admission.room_number if admission else '-'

    get_current_room.short_description = 'Палата'

    def get_status(self, obj):
        admission = obj.admissions.filter(discharge_date__isnull=True).first()
        return "В стационаре" if admission else "Выписан"

    get_status.short_description = 'Статус'


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = (
        'patient',
        'get_hospital',
        'admission_date',
        'discharge_date',
        'department',
        'room_number',
        'severity',
        'diagnosis_short'
    )
    list_filter = ('patient__hospital', 'severity', 'discharge_date')
    search_fields = ('patient__last_name', 'patient__first_name', 'diagnosis')
    ordering = ('-admission_date',)

    def get_hospital(self, obj):
        return obj.patient.hospital.name if obj.patient and obj.patient.hospital else '-'

    get_hospital.short_description = 'Больница'
    get_hospital.admin_order_field = 'patient__hospital'

    def diagnosis_short(self, obj):
        return obj.diagnosis[:50] + '...' if len(obj.diagnosis) > 50 else obj.diagnosis

    diagnosis_short.short_description = 'Диагноз'


class CustomUserAdmin(UserAdmin):
    form = CustomUserDepartmentForm
    filter_horizontal = ('departments', 'groups', 'user_permissions')

    fieldsets = UserAdmin.fieldsets + (
        ('Рабочая информация', {
            'fields': (
                'full_name',
                'position',
                'employee_number',
                'phone_number',
                'hospital',
                'departments'
            )
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Рабочая информация', {
            'fields': (
                'full_name',
                'position',
                'employee_number',
                'phone_number',
                'hospital'
            )
        }),
    )
    list_display = (
        'username',
        'full_name',
        'position',
        'get_hospital',
        'get_departments',
        'is_staff'
    )
    list_filter = ('hospital', 'is_staff', 'is_superuser', 'groups')
    search_fields = ('full_name', 'employee_number', 'phone_number', 'hospital__name')
    ordering = ('hospital', 'full_name')

    def get_hospital(self, obj):
        return obj.hospital.name if obj.hospital else '-'

    get_hospital.short_description = 'Больница'
    get_hospital.admin_order_field = 'hospital'

    def get_departments(self, obj):
        return ", ".join([d.name for d in obj.departments.all()])

    get_departments.short_description = 'Отделения'


if admin.site.is_registered(CustomUser):
    admin.site.unregister(CustomUser)
admin.site.register(CustomUser, CustomUserAdmin)