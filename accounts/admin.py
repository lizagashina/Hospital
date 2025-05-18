from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Department, Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'department', 'room_number', 'severity', 'discharged', 'get_gender_display')
    list_filter = ('department', 'severity', 'discharged')
    search_fields = ('last_name', 'first_name', 'snils')
    ordering = ('-admission_date',)


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'employee_number', 'full_name', 'position', 'phone_number')
    list_filter = ('position', 'departments')
    search_fields = ('username', 'employee_number', 'full_name')
    filter_horizontal = ('departments', 'groups', 'user_permissions')  # Для ManyToMany полей пользователя

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('full_name', 'employee_number', 'phone_number')}),
        ('Должность и отделения', {'fields': ('position', 'departments')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'user_count')
    search_fields = ('name', 'code')

    def user_count(self, obj):
        return obj.customuser_set.count()

    user_count.short_description = 'Количество пользователей'


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Department, DepartmentAdmin)