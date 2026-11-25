from django.test import TestCase, Client
from django.db import connection, IntegrityError
from django.urls import reverse
from accounts.models import User
from facilities.models import Room


class CoreAndDatabaseTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='superadmin',
            password='Password123!',
            email='admin@college.edu',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )

    def test_sqlite_foreign_keys_pragma_enabled(self):
        """
        Verify that PRAGMA foreign_keys is strictly ON in SQLite connections.
        """
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys;")
                fk_status = cursor.fetchone()[0]
                self.assertEqual(fk_status, 1, "SQLite PRAGMA foreign_keys should be 1 (enabled)")

    def test_sqlite_raw_foreign_key_violation_raises_error(self):
        """
        Directly verify SQLite blocks inserting an asset with a non-existent room_id.
        """
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                with self.assertRaises(IntegrityError):
                    cursor.execute(
                        "INSERT INTO facilities_asset (name, asset_tag, category, status, room_id) VALUES (?, ?, ?, ?, ?)",
                        ['Invalid Asset', 'TAG-INVALID-999', 'OTHER', 'OPERATIONAL', 999999]
                    )

    def test_landing_page_renders_for_anonymous_user(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CampusCare')
        self.assertContains(response, 'Unified Portal')

    def test_dashboard_redirects_for_anonymous_user(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_renders_kpis(self):
        self.client.login(username='superadmin', password='Password123!')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Open Maintenance')
        self.assertContains(response, 'Critical / High Priority')

    def test_dynamic_unhighlight_when_feature_visited(self):
        from notices.models import Announcement
        from tickets.models import MaintenanceRequest
        from facilities.models import Room

        room = Room.objects.create(
            building_name='Main Block',
            building_code='MB',
            floor='1st',
            room_number='101',
            capacity=60
        )
        Announcement.objects.create(
            title='Urgent Library Update',
            summary='Library open 24/7 during finals.',
            body='Full details on access.',
            created_by=self.admin
        )
        MaintenanceRequest.objects.create(
            room=room,
            reported_by=self.admin,
            title='Projector Flicker',
            description='Flickering on HDMI',
            category='AV_IT',
            priority='HIGH',
            status='SUBMITTED'
        )

        self.client.login(username='superadmin', password='Password123!')

        # 1. On dashboard, notices and tickets should be highlighted
        dash_response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dash_response.status_code, 200)
        self.assertTrue(dash_response.context['has_new_announcements'])
        self.assertTrue(dash_response.context['has_new_tickets'])

        # 2. Visit Notices list view -> marks notices as visited
        notices_response = self.client.get(reverse('notices:announcement_list'))
        self.assertEqual(notices_response.status_code, 200)

        # 3. Re-check dashboard -> notices is now unhighlighted!
        dash_after_notices = self.client.get(reverse('core:dashboard'))
        self.assertFalse(dash_after_notices.context['has_new_announcements'])
        self.assertTrue(dash_after_notices.context['has_new_tickets'])

        # 4. Visit Tickets list view -> marks tickets as visited
        tickets_response = self.client.get(reverse('tickets:ticket_list'))
        self.assertEqual(tickets_response.status_code, 200)

        # 5. Re-check dashboard -> tickets is now also unhighlighted!
        dash_after_all = self.client.get(reverse('core:dashboard'))
        self.assertFalse(dash_after_all.context['has_new_announcements'])
        self.assertFalse(dash_after_all.context['has_new_tickets'])
