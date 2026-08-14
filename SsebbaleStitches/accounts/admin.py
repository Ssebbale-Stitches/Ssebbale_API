from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import OTP, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "full_name", "is_email_verified", "is_tailor", "is_active", "date_joined"]
    list_filter = ["is_email_verified", "is_tailor", "is_active", "is_staff"]
    search_fields = ["email", "full_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "phone")}),
        ("Status", {"fields": ("is_active", "is_staff", "is_superuser", "is_email_verified", "is_tailor")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ["user", "purpose", "code", "created_at", "expires_at", "is_used"]
    list_filter = ["purpose", "is_used"]
    search_fields = ["user__email", "code"]
