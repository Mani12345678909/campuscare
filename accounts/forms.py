from django import forms
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from .models import User


class UserRegistrationForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=[(User.Role.STUDENT, 'Student'), (User.Role.FACULTY, 'Faculty')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select your college role. Staff/Admins are designated by system administrators."
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter secure password'}),
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat your password'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'department', 'identifier_number', 'phone_number']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., alex.smith'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'username@college.edu'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science, Mechanical'}),
            'identifier_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Roll No. (Student) or Emp ID (Faculty)'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 019-2834'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email or '@' not in email:
            raise forms.ValidationError("Please provide a valid email address.")

        from .models import AllowedEmailDomain
        if not AllowedEmailDomain.is_domain_allowed(email):
            allowed_domains = AllowedEmailDomain.get_allowed_domain_list()
            allowed_str = ", ".join([f"@{d}" for d in allowed_domains])
            domain = email.split('@')[-1]
            raise forms.ValidationError(
                f"Registration is restricted to authorized college-domain emails ({allowed_str}). Domain @{domain} is not authorized."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        # New signups must complete first-login 2FA and onboarding
        user.is_first_login_2fa_completed = False
        user.is_onboarding_completed = False
        if commit:
            user.save()
        return user


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center font-monospace fs-3 tracking-widest',
            'placeholder': '123456',
            'autocomplete': 'one-time-code',
            'autofocus': True,
        }),
        help_text="Enter the 6-digit verification code sent to your registered college email."
    )


class OnboardingForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'department', 'identifier_number', 'year_or_block', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science & Engineering'}),
            'identifier_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Roll No. (e.g. 21CS042) or Emp ID'}),
            'year_or_block': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3rd Year / Section B or Ramanujan Block'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+1 (555) 012-3456'}),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'department', 'identifier_number', 'year_or_block', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'identifier_number': forms.TextInput(attrs={'class': 'form-control'}),
            'year_or_block': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserRoleUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role', 'department', 'identifier_number', 'year_or_block', 'is_active', 'is_first_login_2fa_completed', 'is_onboarding_completed']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'identifier_number': forms.TextInput(attrs={'class': 'form-control'}),
            'year_or_block': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_first_login_2fa_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_onboarding_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AllowedEmailDomainForm(forms.ModelForm):
    class Meta:
        from .models import AllowedEmailDomain
        model = AllowedEmailDomain
        fields = ['domain', 'college_name', 'is_active']
        widgets = {
            'domain': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., mit.edu, stanford.edu, engg.ac.in (without @)'
            }),
            'college_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Massachusetts Institute of Technology'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_domain(self):
        domain = self.cleaned_data.get('domain', '').strip().lower()
        if domain.startswith('@'):
            domain = domain[1:]
        if not domain or '.' not in domain or ' ' in domain:
            raise forms.ValidationError("Please provide a valid domain name without '@' (e.g., college.edu).")
        return domain
