from datetime import date
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from facilities.models import Room
from notices.models import Announcement, FeeRecord
from tickets.models import MaintenanceRequest


class NoticesAndReportsTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.admin = User.objects.create_superuser(
            username='admin_boss',
            email='boss@college.edu',
            password='Password123!',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.student = User.objects.create_user(
            username='student_eva',
            email='eva@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            identifier_number='21CS050',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.room = Room.objects.create(
            building_name='Newton Science Block',
            building_code='NWT',
            floor='1st',
            room_number='101',
            capacity=50
        )

    def test_announcements_and_filtering(self):
        Announcement.objects.create(
            title='Campus Sports Meet 2026',
            summary='Inter-department athletics.',
            body='Track and field events start at 9am.',
            announcement_type=Announcement.Type.EVENT,
            target_role=Announcement.TargetRole.ALL,
            created_by=self.admin
        )
        Announcement.objects.create(
            title='Staff Salary Revision Notice',
            summary='Internal administrative memo.',
            body='Payroll updates for Q4.',
            announcement_type=Announcement.Type.GENERAL,
            target_role=Announcement.TargetRole.STAFF,
            created_by=self.admin
        )

        self.client.login(username='student_eva', password='Password123!')
        response = self.client.get(reverse('notices:announcement_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Campus Sports Meet 2026')
        # Student should NOT see STAFF-only memo
        self.assertNotContains(response, 'Staff Salary Revision Notice')

    def test_announcement_detail_view(self):
        announcement = Announcement.objects.create(
            title='Annual Convocation 2026',
            summary='Graduation ceremony details.',
            body='Full details on gowns and seating.',
            announcement_type=Announcement.Type.EVENT,
            target_role=Announcement.TargetRole.ALL,
            created_by=self.admin
        )
        self.client.login(username='student_eva', password='Password123!')
        response = self.client.get(reverse('notices:announcement_detail', args=[announcement.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Annual Convocation 2026')
        self.assertContains(response, 'Graduation ceremony details.')

    def test_fee_tracker_and_dues_calculation(self):
        FeeRecord.objects.create(
            student=self.student,
            academic_term='Fall 2026',
            fee_category='Tuition Fee',
            amount=Decimal('3000.00'),
            due_date=date(2026, 12, 1),
            status=FeeRecord.Status.PENDING
        )
        FeeRecord.objects.create(
            student=self.student,
            academic_term='Fall 2026',
            fee_category='Hostel Fee',
            amount=Decimal('800.00'),
            due_date=date(2026, 11, 1),
            status=FeeRecord.Status.PAID,
            paid_date=date(2026, 10, 25),
            receipt_number='REC-991'
        )

        self.client.login(username='student_eva', password='Password123!')
        response = self.client.get(reverse('notices:fee_tracker'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '$3000.00')
        self.assertContains(response, 'REC-991')

    def test_csv_export_endpoints(self):
        # Create ticket for maintenance export
        MaintenanceRequest.objects.create(
            room=self.room,
            reported_by=self.student,
            title='AC Filter Cleaning',
            description='Filter dusty.',
            category=MaintenanceRequest.Category.HVAC,
            priority=MaintenanceRequest.Priority.LOW,
            status=MaintenanceRequest.Status.SUBMITTED
        )

        self.client.login(username='admin_boss', password='Password123!')

        # 1. Maintenance CSV Export
        m_resp = self.client.get(reverse('notices:export_maintenance_csv'))
        self.assertEqual(m_resp.status_code, 200)
        self.assertEqual(m_resp['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="maintenance_room_faults_report.csv"', m_resp['Content-Disposition'])
        self.assertIn(b'AC Filter Cleaning', m_resp.content)

        # 2. Attendance CSV Export
        a_resp = self.client.get(reverse('notices:export_attendance_csv'))
        self.assertEqual(a_resp.status_code, 200)
        self.assertEqual(a_resp['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="student_attendance_summary_report.csv"', a_resp['Content-Disposition'])

        # 3. Teacher Activity CSV Export
        t_resp = self.client.get(reverse('notices:export_teacher_activity_csv'))
        self.assertEqual(t_resp.status_code, 200)
        self.assertEqual(t_resp['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="teacher_activity_class_log_report.csv"', t_resp['Content-Disposition'])

    def test_live_watch_feed_endpoint(self):
        self.client.login(username='student_eva', password='Password123!')
        response = self.client.get(reverse('notices:live_feed'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Campus Watch & Live Operations Feed')
