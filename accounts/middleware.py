from django.shortcuts import redirect
from django.urls import reverse


class FirstLoginEnforcementMiddleware:
    """
    Blocks access to main operational dashboards until:
    1. First-login 2FA verification is completed.
    2. Initial onboarding profile setup is completed.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path

            # Allowed paths during 2FA & Onboarding
            allowed_prefixes = [
                reverse('accounts:verify_2fa'),
                reverse('accounts:resend_otp'),
                reverse('accounts:onboarding'),
                reverse('accounts:logout'),
                '/static/',
                '/media/',
            ]
            if request.user.is_superuser or request.user.is_staff:
                allowed_prefixes.append('/admin/')

            is_allowed = any(path.startswith(prefix) for prefix in allowed_prefixes)

            if not is_allowed:
                if not request.user.is_first_login_2fa_completed:
                    return redirect('accounts:verify_2fa')
                if not request.user.is_onboarding_completed:
                    return redirect('accounts:onboarding')

        return self.get_response(request)

