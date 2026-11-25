from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from accounts.models import User, OTPVerification


class AccountsAnd2FATests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='student1',
            email='student1@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='One',
            identifier_number='21CS001',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.faculty = User.objects.create_user(
            username='prof1',
            email='prof1@college.edu',
            password='Password123!',
            role=User.Role.FACULTY,
            first_name='Professor',
            last_name='One',
            identifier_number='EMP-FAC-01',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.manager = User.objects.create_user(
            username='manager1',
            email='manager1@college.edu',
            password='Password123!',
            role=User.Role.MANAGER,
            first_name='Manager',
            last_name='One',
            is_staff=True,
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.admin = User.objects.create_superuser(
            username='admin1',
            email='admin1@college.edu',
            password='Password123!',
            role=User.Role.ADMIN,
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )

    def test_college_email_domain_validation_on_registration(self):
        # 1. Reject non-college email domain (e.g. gmail.com)
        response_invalid = self.client.post(reverse('accounts:register'), {
            'username': 'external_user',
            'email': 'external@gmail.com',
            'first_name': 'External',
            'last_name': 'User',
            'role': User.Role.STUDENT,
            'department': 'Computer Science',
            'identifier_number': '21CS999',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertEqual(response_invalid.status_code, 200)
        self.assertContains(response_invalid, "restricted to authorized college-domain emails")

        # 2. Accept approved college email domain
        response_valid = self.client.post(reverse('accounts:register'), {
            'username': 'valid_student',
            'email': 'valid_student@college.edu',
            'first_name': 'Valid',
            'last_name': 'Student',
            'role': User.Role.STUDENT,
            'department': 'Computer Science',
            'identifier_number': '21CS100',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        # Should redirect to 2FA verification
        self.assertEqual(response_valid.status_code, 302)
        self.assertRedirects(response_valid, reverse('accounts:verify_2fa'))

        # Check user created and OTP generated in mail
        user = User.objects.get(username='valid_student')
        self.assertFalse(user.is_first_login_2fa_completed)
        self.assertFalse(user.is_onboarding_completed)
        self.assertTrue(len(mail.outbox) > 0)
        self.assertIn("CampusCare Verification Code", mail.outbox[-1].subject)

    def test_first_login_2fa_otp_verification_and_onboarding_flow(self):
        # Create unverified user
        unverified_user = User.objects.create_user(
            username='fresh_user',
            email='fresh@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            is_first_login_2fa_completed=False,
            is_onboarding_completed=False
        )

        # Login
        login_resp = self.client.post(reverse('accounts:login'), {
            'username': 'fresh_user',
            'password': 'Password123!',
        })
        self.assertEqual(login_resp.status_code, 302)
        self.assertRedirects(login_resp, reverse('accounts:verify_2fa'))

        # Attempting to access dashboard should be blocked by middleware and redirect to 2FA
        dash_resp = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dash_resp.status_code, 302)
        self.assertRedirects(dash_resp, reverse('accounts:verify_2fa'))

        # Fetch active OTP
        otp_record = unverified_user.otp_verifications.filter(is_used=False).latest('created_at')

        # Test wrong OTP rejected
        bad_verify = self.client.post(reverse('accounts:verify_2fa'), {'otp_code': '000000'})
        self.assertEqual(bad_verify.status_code, 200)
        self.assertContains(bad_verify, "Incorrect verification code")

        # Submit correct OTP
        good_verify = self.client.post(reverse('accounts:verify_2fa'), {'otp_code': otp_record.otp_code})
        self.assertEqual(good_verify.status_code, 302)
        self.assertRedirects(good_verify, reverse('accounts:onboarding'))

        unverified_user.refresh_from_db()
        self.assertTrue(unverified_user.is_first_login_2fa_completed)
        self.assertFalse(unverified_user.is_onboarding_completed)

        # Complete onboarding step
        onboard_resp = self.client.post(reverse('accounts:onboarding'), {
            'first_name': 'Fresh',
            'last_name': 'Person',
            'department': 'Mechanical Engineering',
            'identifier_number': '21ME050',
            'year_or_block': '2nd Year / Section A',
            'phone_number': '555-0199',
        })
        self.assertEqual(onboard_resp.status_code, 302)
        self.assertRedirects(onboard_resp, reverse('core:dashboard'))

        unverified_user.refresh_from_db()
        self.assertTrue(unverified_user.is_onboarding_completed)
        self.assertEqual(unverified_user.department, 'Mechanical Engineering')

    def test_permission_restrictions(self):
        # Student cannot access staff user management
        self.client.login(username='student1', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 403)

        # Manager can access
        self.client.login(username='manager1', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_domain_management_and_dynamic_registration(self):
        from accounts.models import AllowedEmailDomain

        # Student denied access to domain control center
        self.client.login(username='student1', password='Password123!')
        res_denied = self.client.get(reverse('accounts:domain_list'))
        self.assertEqual(res_denied.status_code, 403)

        # Admin accesses domain control center
        self.client.login(username='admin1', password='Password123!')
        res_admin = self.client.get(reverse('accounts:domain_list'))
        self.assertEqual(res_admin.status_code, 200)

        # Admin adds 'mit.edu'
        res_add = self.client.post(reverse('accounts:domain_list'), {
            'domain': 'mit.edu',
            'college_name': 'MIT',
            'is_active': True,
        })
        self.assertEqual(res_add.status_code, 302)
        self.assertTrue(AllowedEmailDomain.objects.filter(domain='mit.edu', is_active=True).exists())

        # Registration with @mit.edu is now accepted
        self.client.logout()
        res_reg = self.client.post(reverse('accounts:register'), {
            'username': 'mit_scholar',
            'email': 'scholar@mit.edu',
            'first_name': 'MIT',
            'last_name': 'Scholar',
            'role': User.Role.STUDENT,
            'department': 'Robotics',
            'identifier_number': 'MIT-991',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertEqual(res_reg.status_code, 302)
        self.assertTrue(User.objects.filter(username='mit_scholar').exists())

        # Toggle 'mit.edu' to inactive
        self.client.login(username='admin1', password='Password123!')
        mit_dom = AllowedEmailDomain.objects.get(domain='mit.edu')
        self.client.get(reverse('accounts:domain_toggle', args=[mit_dom.id]))
        mit_dom.refresh_from_db()
        self.assertFalse(mit_dom.is_active)

        # New registration with @mit.edu should now be rejected
        self.client.logout()
        res_reg_disabled = self.client.post(reverse('accounts:register'), {
            'username': 'mit_scholar2',
            'email': 'scholar2@mit.edu',
            'first_name': 'MIT',
            'last_name': 'Scholar2',
            'role': User.Role.STUDENT,
            'department': 'Robotics',
            'identifier_number': 'MIT-992',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
        })
        self.assertEqual(res_reg_disabled.status_code, 200)
        self.assertContains(res_reg_disabled, "Domain @mit.edu is not authorized.")
