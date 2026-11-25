from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-2fa/', views.verify_2fa_view, name='verify_2fa'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:user_id>/edit-role/', views.user_edit_role_view, name='user_edit_role'),
    path('domains/', views.domain_list_view, name='domain_list'),
    path('domains/<int:domain_id>/toggle/', views.domain_toggle_view, name='domain_toggle'),
    path('domains/<int:domain_id>/delete/', views.domain_delete_view, name='domain_delete'),
]
