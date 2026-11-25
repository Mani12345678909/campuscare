from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from facilities.models import Room, Asset
from tickets.models import MaintenanceRequest, TicketUpdate


class TicketsWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.reporter = User.objects.create_user(
            username='student_sam',
            password='Password123!',
            role=User.Role.STUDENT,
            first_name='Sam',
            last_name='Student',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.other_reporter = User.objects.create_user(
            username='faculty_jane',
            password='Password123!',
            role=User.Role.FACULTY,
            first_name='Jane',
            last_name='Faculty',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.technician = User.objects.create_user(
            username='tech_dave',
            password='Password123!',
            role=User.Role.TECHNICIAN,
            first_name='Dave',
            last_name='Tech',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.manager = User.objects.create_user(
            username='manager_alice',
            password='Password123!',
            role=User.Role.MANAGER,
            first_name='Alice',
            last_name='Manager',
            is_staff=True,
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )

        self.room = Room.objects.create(
            building_name='Engineering Hall',
            building_code='ENG',
            floor='2nd',
            room_number='201',
            room_type=Room.RoomType.LAB,
            capacity=40
        )
        self.asset = Asset.objects.create(
            room=self.room,
            name='Oscilloscope Station',
            asset_tag='AST-ENG201-01',
            category=Asset.Category.ELECTRICAL,
            status=Asset.Condition.OPERATIONAL
        )

    def test_auto_ticket_code_generation(self):
        year = timezone.now().year
        ticket1 = MaintenanceRequest.objects.create(
            room=self.room,
            asset=self.asset,
            reported_by=self.reporter,
            title='Oscilloscope power failure',
            description='Unit does not power on.',
            category=MaintenanceRequest.Category.ELECTRICAL,
            priority=MaintenanceRequest.Priority.HIGH,
        )
        self.assertTrue(ticket1.ticket_code.startswith(f"CM-{year}-"))
        self.assertEqual(ticket1.ticket_code, f"CM-{year}-0001")

        ticket2 = MaintenanceRequest.objects.create(
            room=self.room,
            reported_by=self.reporter,
            title='Broken power strip in bench 2',
            description='Sparks observed.',
            category=MaintenanceRequest.Category.ELECTRICAL,
            priority=MaintenanceRequest.Priority.CRITICAL,
        )
        self.assertEqual(ticket2.ticket_code, f"CM-{year}-0002")

    def test_reporter_can_submit_ticket(self):
        self.client.login(username='student_sam', password='Password123!')
        response = self.client.post(reverse('tickets:ticket_create'), {
            'report_type': MaintenanceRequest.ReportType.MAINTENANCE,
            'room': self.room.id,
            'asset': self.asset.id,
            'category': MaintenanceRequest.Category.ELECTRICAL,
            'priority': MaintenanceRequest.Priority.MEDIUM,
            'title': 'Fuse blown on bench 1',
            'description': 'Power cut off when multimeter was attached.',
        })
        self.assertEqual(response.status_code, 302)
        ticket = MaintenanceRequest.objects.get(title='Fuse blown on bench 1')
        self.assertEqual(ticket.reported_by, self.reporter)
        self.assertEqual(ticket.status, MaintenanceRequest.Status.SUBMITTED)
        self.assertEqual(ticket.updates.count(), 1)
        self.assertEqual(ticket.updates.first().author, self.reporter)

    def test_reporter_cannot_update_status_or_resolve_ticket(self):
        ticket = MaintenanceRequest.objects.create(
            room=self.room,
            reported_by=self.other_reporter,
            title='Projector flicker',
            description='Flickering image.',
            category=MaintenanceRequest.Category.AV_IT,
            priority=MaintenanceRequest.Priority.MEDIUM,
        )

        self.client.login(username='student_sam', password='Password123!')
        response = self.client.post(
            reverse('tickets:ticket_update_status', args=[ticket.ticket_code]),
            {
                'status': MaintenanceRequest.Status.RESOLVED,
                'comment': 'Attempting unauthorized resolve',
                'resolution_notes': 'Fake resolution',
            }
        )
        self.assertEqual(response.status_code, 403)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, MaintenanceRequest.Status.SUBMITTED)
        self.assertIsNone(ticket.resolved_at)

    def test_reporter_cannot_assign_ticket(self):
        ticket = MaintenanceRequest.objects.create(
            room=self.room,
            reported_by=self.reporter,
            title='Fume hood sensor beep',
            description='Audible alarm sounding.',
            category=MaintenanceRequest.Category.HVAC,
            priority=MaintenanceRequest.Priority.HIGH,
        )

        self.client.login(username='student_sam', password='Password123!')
        response = self.client.post(
            reverse('tickets:ticket_assign', args=[ticket.ticket_code]),
            {
                'assigned_to': self.technician.id,
                'priority': MaintenanceRequest.Priority.LOW,
                'status': MaintenanceRequest.Status.ASSIGNED,
            }
        )
        self.assertEqual(response.status_code, 403)

    def test_technician_workflow_and_ticket_update_history(self):
        ticket = MaintenanceRequest.objects.create(
            room=self.room,
            asset=self.asset,
            reported_by=self.reporter,
            assigned_to=self.technician,
            title='Oscilloscope probe broken',
            description='Probe B lead severed.',
            category=MaintenanceRequest.Category.ELECTRICAL,
            priority=MaintenanceRequest.Priority.MEDIUM,
            status=MaintenanceRequest.Status.ASSIGNED,
        )

        self.client.login(username='tech_dave', password='Password123!')

        # 1. Move to IN_PROGRESS
        response1 = self.client.post(
            reverse('tickets:ticket_update_status', args=[ticket.ticket_code]),
            {
                'status': MaintenanceRequest.Status.IN_PROGRESS,
                'comment': 'Picked up replacement probe from inventory. Testing on bench.',
            }
        )
        self.assertEqual(response1.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, MaintenanceRequest.Status.IN_PROGRESS)
        self.assertIsNone(ticket.resolved_at)

        # 2. Move to RESOLVED
        response2 = self.client.post(
            reverse('tickets:ticket_update_status', args=[ticket.ticket_code]),
            {
                'status': MaintenanceRequest.Status.RESOLVED,
                'comment': 'Replacement installed and tested with 1kHz calibration wave.',
                'resolution_notes': 'Replaced broken BNC probe lead with brand new 100MHz probe.',
            }
        )
        self.assertEqual(response2.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, MaintenanceRequest.Status.RESOLVED)
        self.assertIsNotNone(ticket.resolved_at)
        self.assertIn('Replaced broken BNC probe', ticket.resolution_notes)

        updates = ticket.updates.order_by('created_at')
        self.assertEqual(updates.count(), 2)
        self.assertEqual(updates[0].new_status, MaintenanceRequest.Status.IN_PROGRESS)
        self.assertEqual(updates[1].new_status, MaintenanceRequest.Status.RESOLVED)
        self.assertEqual(updates[1].author, self.technician)

    def test_manager_can_assign_and_triage(self):
        ticket = MaintenanceRequest.objects.create(
            room=self.room,
            reported_by=self.reporter,
            title='AC leaking',
            description='Water pooling.',
            category=MaintenanceRequest.Category.HVAC,
            priority=MaintenanceRequest.Priority.MEDIUM,
            status=MaintenanceRequest.Status.SUBMITTED,
        )

        self.client.login(username='manager_alice', password='Password123!')
        response = self.client.post(
            reverse('tickets:ticket_assign', args=[ticket.ticket_code]),
            {
                'assigned_to': self.technician.id,
                'priority': MaintenanceRequest.Priority.CRITICAL,
                'status': MaintenanceRequest.Status.ASSIGNED,
                'comment': 'High priority triage due to water pooling danger.',
            }
        )
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to, self.technician)
        self.assertEqual(ticket.priority, MaintenanceRequest.Priority.CRITICAL)
        self.assertEqual(ticket.status, MaintenanceRequest.Status.ASSIGNED)
        self.assertTrue(ticket.updates.filter(author=self.manager).exists())

    def test_duplicate_check_api(self):
        MaintenanceRequest.objects.create(
            room=self.room,
            asset=self.asset,
            reported_by=self.reporter,
            title='Existing open issue on asset',
            description='Active issue.',
            status=MaintenanceRequest.Status.SUBMITTED,
        )

        self.client.login(username='student_sam', password='Password123!')
        response = self.client.get(
            reverse('tickets:check_duplicates_api'),
            {'room_id': self.room.id, 'asset_id': self.asset.id}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['tickets']), 1)
        self.assertEqual(data['tickets'][0]['title'], 'Existing open issue on asset')
