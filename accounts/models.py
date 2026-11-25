import random
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        FACULTY = 'FACULTY', 'Faculty'
        TECHNICIAN = 'TECHNICIAN', 'Technician'
        MANAGER = 'MANAGER', 'Facility / Dept Manager'
        ADMIN = 'ADMIN', 'Administrator'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
        help_text="Designates the system role and permission tier of the user."
    )
    department = models.CharField(max_length=120, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    identifier_number = models.CharField(
        max_length=60,
        blank=True,
        help_text="Roll Number (for Students) or Employee ID (for Faculty/Staff)"
    )
    year_or_block = models.CharField(
        max_length=60,
        blank=True,
        help_text="Year & Section (e.g., 3rd Year - Sec A) or Assigned Block"
    )

    # First-login 2FA and Onboarding flags
    is_first_login_2fa_completed = models.BooleanField(
        default=False,
        help_text="Designates whether the user has completed their first-login two-step verification."
    )
    is_onboarding_completed = models.BooleanField(
        default=False,
        help_text="Designates whether the user has completed their initial onboarding profile confirmation."
    )

    # Feature visit timestamps for dynamic unhighlighting
    last_seen_notices_at = models.DateTimeField(null=True, blank=True)
    last_seen_tickets_at = models.DateTimeField(null=True, blank=True)
    last_seen_timetable_at = models.DateTimeField(null=True, blank=True)

    def mark_feature_visited(self, feature):
        """
        Updates the last visited timestamp so new data highlights/badges
        automatically clear when the user visits that section.
        """
        now = timezone.now()
        if feature == 'notices':
            self.last_seen_notices_at = now
            self.save(update_fields=['last_seen_notices_at'])
        elif feature == 'tickets':
            self.last_seen_tickets_at = now
            self.save(update_fields=['last_seen_tickets_at'])
        elif feature == 'timetable':
            self.last_seen_timetable_at = now
            self.save(update_fields=['last_seen_timetable_at'])

    class Meta:
        ordering = ['username']

    def __str__(self):
        full_name = self.get_full_name()
        display = full_name if full_name else self.username
        return f"{display} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_faculty(self):
        return self.role == self.Role.FACULTY

    @property
    def is_reporter(self):
        """Students and Faculty act as problem reporters."""
        return self.role in [self.Role.STUDENT, self.Role.FACULTY]

    @property
    def is_technician(self):
        return self.role == self.Role.TECHNICIAN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER or self.is_superuser

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser


class OTPVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_verifications')
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def generate_otp(cls, user, validity_minutes=10):
        # Invalidate any prior unused OTPs
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        code = f"{random.randint(100000, 999999)}"
        expiry = timezone.now() + timedelta(minutes=validity_minutes)
        return cls.objects.create(
            user=user,
            otp_code=code,
            expires_at=expiry,
        )

    def is_valid(self):
        return not self.is_used and self.attempts < 5 and timezone.now() <= self.expires_at

    def __str__(self):
        return f"OTP for {self.user.username} (Expires: {self.expires_at:%H:%M:%S})"


class AllowedEmailDomain(models.Model):
    domain = models.CharField(
        max_length=100,
        unique=True,
        help_text="Domain name without @ (e.g., college.edu, stanford.edu, campus.ac.in)"
    )
    college_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Full Name of the College or University"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether new users with this email domain can register or log in."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_domains'
    )

    class Meta:
        ordering = ['domain']
        verbose_name = "Allowed College Email Domain"
        verbose_name_plural = "Allowed College Email Domains"

    def __str__(self):
        if self.college_name:
            return f"@{self.domain} ({self.college_name})"
        return f"@{self.domain}"

    @classmethod
    def get_allowed_domain_list(cls):
        """
        Retrieves active database domains combined with settings.ALLOWED_EMAIL_DOMAINS fallback.
        """
        from django.conf import settings
        try:
            db_domains = list(cls.objects.filter(is_active=True).values_list('domain', flat=True))
        except Exception:
            db_domains = []
        fallback = getattr(settings, 'ALLOWED_EMAIL_DOMAINS', ['college.edu', 'university.edu'])
        combined = set([d.strip().lower() for d in db_domains if d] + [d.strip().lower() for d in fallback if d])
        return sorted(list(combined))

    @classmethod
    def is_domain_allowed(cls, email_or_domain):
        if not email_or_domain:
            return False
        if '@' in email_or_domain:
            domain = email_or_domain.split('@')[-1].strip().lower()
        else:
            domain = email_or_domain.strip().lower()
        return domain in cls.get_allowed_domain_list()
