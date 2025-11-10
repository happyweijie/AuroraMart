from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Customer, AdminProfile


User = get_user_model()


class CustomerAdmin(admin.ModelAdmin):
	list_display = ("user", "age", "gender", "employment_status", "monthly_income_sgd", "created_at")
	search_fields = ("user__username", "user__email")
	list_filter = ("gender", "employment_status")
	readonly_fields = ("created_at", "updated_at")


class AdminProfileAdmin(admin.ModelAdmin):
	list_display = ("user", "position", "department", "created_at")
	search_fields = ("user__username",)
	list_filter = ("position", "department")
	readonly_fields = ("created_at", "updated_at")


class UserAdmin(admin.ModelAdmin):
	list_display = ("username", "email", "is_staff", "is_active")
	search_fields = ("username", "email")
	list_filter = ("is_staff", "is_active")


admin.site.register(User, UserAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(AdminProfile, AdminProfileAdmin)
