from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPVerification, AllowedEmailDomain


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'role', 'department', 'identifier_number',
        'is_first_login_2fa_completed', 'is_onboarding_completed'
    )
    list_filter = ('role', 'is_first_login_2fa_completed', 'is_onboarding_completed', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'identifier_number', 'department')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Academic & Campus Details', {
            'fields': (
                'role', 'department', 'identifier_number', 'year_or_block',
                'phone_number', 'is_first_login_2fa_completed', 'is_onboarding_completed'
            )
        }),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_code', 'created_at', 'expires_at', 'attempts', 'is_used')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email', 'otp_code')
    readonly_fields = ('created_at',)


@admin.register(AllowedEmailDomain)
class AllowedEmailDomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'college_name', 'is_active', 'created_by', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('domain', 'college_name')
    readonly_fields = ('created_at',)
