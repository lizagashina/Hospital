from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Department, Patient, Admission


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        'last_name',
        'first_name',
        'get_current_department',
        'get_current_room',
        'get_status',
        'snils',
        'birth_date'
    )
    list_filter = ('gender',)
    search_fields = ('last_name', 'first_name', 'middle_name', 'snils')
    ordering = ('last_name', 'first_name')

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
        'admission_date',
        'discharge_date',
        'department',
        'room_number',
        'severity',
        'diagnosis_short'
    )
    list_filter = ('department', 'severity', 'discharge_date')
    search_fields = ('patient__last_name', 'patient__first_name', 'diagnosis')
    ordering = ('-admission_date',)

    def diagnosis_short(self, obj):
        return obj.diagnosis[:50] + '...' if len(obj.diagnosis) > 50 else obj.diagnosis

    diagnosis_short.short_description = 'Диагноз'