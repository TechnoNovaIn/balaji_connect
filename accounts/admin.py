from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employee, Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'created_at')
    search_fields = ('code', 'name')


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = ('employee_id', 'username', 'first_name', 'last_name', 'department', 'designation', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'department')
    search_fields = ('employee_id', 'username', 'first_name', 'last_name', 'email')
    ordering = ('employee_id',)

    fieldsets = (
        (None, {'fields': ('employee_id', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'avatar_url')}),
        ('Company Details', {'fields': ('department', 'designation', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')
