from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import User, OTPVerification, AllowedEmailDomain
from .forms import (
    UserRegistrationForm,
    OTPVerificationForm,
    OnboardingForm,
    UserProfileForm,
    UserRoleUpdateForm,
    AllowedEmailDomainForm
)
from .permissions import manager_required, admin_required


def send_otp_email(user, otp_record):
    """
    Sends the 6-digit OTP to the user's college email.
    Uses console email backend in dev/test for easy inspection.
    """
    subject = f"CampusCare Verification Code: {otp_record.otp_code}"
    message = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Your one-time 2FA verification code for CampusCare is:\n\n"
        f"    {otp_record.otp_code}\n\n"
        f"This code will expire in 10 minutes. If you did not request this login, please contact campus IT immediately.\n\n"
        f"CampusCare Facilities & Academic Operations"
    )
    send_mail(
        subject,
        message,
        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@college.edu'),
        [user.email],
        fail_silently=False,
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Generate and dispatch initial 2FA OTP
            otp = OTPVerification.generate_otp(user)
            send_otp_email(user, otp)
            login(request, user)
            messages.success(
                request,
                f"Welcome, {user.first_name or user.username}! A 6-digit verification code has been dispatched to {user.email}."
            )
            return redirect('accounts:verify_2fa')
        else:
            messages.error(request, "Please correct the registration errors below.")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or 'core:dashboard'

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # If user has not completed first-login 2FA, generate OTP and redirect
            if not user.is_first_login_2fa_completed:
                otp = OTPVerification.generate_otp(user)
                send_otp_email(user, otp)
                messages.info(
                    request,
                    f"First login detected! A 6-digit security code has been sent to {user.email}."
                )
                return redirect('accounts:verify_2fa')

            if not user.is_onboarding_completed:
                return redirect('accounts:onboarding')

            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('accounts:login')


@login_required
def verify_2fa_view(request):
    user = request.user
    if user.is_first_login_2fa_completed:
        if not user.is_onboarding_completed:
            return redirect('accounts:onboarding')
        return redirect('core:dashboard')

    latest_otp = user.otp_verifications.filter(is_used=False).order_by('-created_at').first()

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['otp_code'].strip()

            if not latest_otp or not latest_otp.is_valid():
                messages.error(request, "Verification code has expired or is invalid. Please request a new code.")
            elif latest_otp.otp_code != code:
                latest_otp.attempts += 1
                latest_otp.save()
                remaining = max(0, 5 - latest_otp.attempts)
                messages.error(request, f"Incorrect verification code. {remaining} attempt(s) remaining.")
            else:
                # Valid OTP!
                latest_otp.is_used = True
                latest_otp.save()
                user.is_first_login_2fa_completed = True
                user.save()

                messages.success(request, "Two-step verification completed successfully!")
                if not user.is_onboarding_completed:
                    return redirect('accounts:onboarding')
                return redirect('core:dashboard')
    else:
        form = OTPVerificationForm()

    return render(request, 'accounts/verify_2fa.html', {
        'form': form,
        'user_email': user.email,
        'latest_otp': latest_otp,
    })


@login_required
def resend_otp_view(request):
    user = request.user
    if user.is_first_login_2fa_completed:
        return redirect('core:dashboard')

    otp = OTPVerification.generate_otp(user)
    send_otp_email(user, otp)
    messages.success(request, f"A fresh verification code has been dispatched to {user.email}.")
    return redirect('accounts:verify_2fa')


@login_required
def onboarding_view(request):
    user = request.user
    if user.is_onboarding_completed:
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = OnboardingForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_onboarding_completed = True
            user.save()
            messages.success(
                request,
                f"Onboarding complete! Welcome to your CampusCare {user.get_role_display()} dashboard."
            )
            return redirect('core:dashboard')
    else:
        form = OnboardingForm(instance=user)

    return render(request, 'accounts/onboarding.html', {
        'form': form,
        'user': user,
    })


@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=user)

    recent_reported = user.reported_tickets.select_related('room', 'asset').order_by('-created_at')[:5]
    recent_assigned = user.assigned_tickets.select_related('room', 'asset').order_by('-created_at')[:5] if user.is_technician else []

    return render(request, 'accounts/profile.html', {
        'form': form,
        'recent_reported': recent_reported,
        'recent_assigned': recent_assigned,
    })


@login_required
@manager_required
def user_list_view(request):
    role_filter = request.GET.get('role', '')
    users = User.objects.all().order_by('username')
    if role_filter:
        users = users.filter(role=role_filter)

    return render(request, 'accounts/user_list.html', {
        'users': users,
        'role_filter': role_filter,
        'roles': User.Role.choices,
    })


@login_required
@manager_required
def user_edit_role_view(request, user_id):
    target_user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = UserRoleUpdateForm(request.POST, instance=target_user)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"User {target_user.username}'s settings updated successfully."
            )
            return redirect('accounts:user_list')
    else:
        form = UserRoleUpdateForm(instance=target_user)

    return render(request, 'accounts/user_edit_role.html', {
        'target_user': target_user,
        'form': form,
    })


@login_required
@admin_required
def domain_list_view(request):
    """
    Admin control center to view and configure allowed college email domains.
    """
    if request.method == 'POST':
        form = AllowedEmailDomainForm(request.POST)
        if form.is_valid():
            domain_obj = form.save(commit=False)
            domain_obj.created_by = request.user
            domain_obj.save()
            messages.success(request, f"College domain @{domain_obj.domain} added successfully.")
            return redirect('accounts:domain_list')
        else:
            messages.error(request, "Failed to add domain. Please review the errors below.")
    else:
        form = AllowedEmailDomainForm()

    domains = AllowedEmailDomain.objects.select_related('created_by').order_by('domain')
    active_domains_count = domains.filter(is_active=True).count()
    fallback_domains = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', ['college.edu', 'university.edu'])

    return render(request, 'accounts/domain_list.html', {
        'domains': domains,
        'form': form,
        'active_domains_count': active_domains_count,
        'fallback_domains': fallback_domains,
    })


@login_required
@admin_required
def domain_toggle_view(request, domain_id):
    domain = get_object_or_404(AllowedEmailDomain, pk=domain_id)
    domain.is_active = not domain.is_active
    domain.save()
    status_str = "activated" if domain.is_active else "deactivated"
    messages.info(request, f"Domain @{domain.domain} has been {status_str}.")
    return redirect('accounts:domain_list')


@login_required
@admin_required
def domain_delete_view(request, domain_id):
    domain = get_object_or_404(AllowedEmailDomain, pk=domain_id)
    dom_name = domain.domain
    domain.delete()
    messages.success(request, f"Domain @{dom_name} was removed.")
    return redirect('accounts:domain_list')
