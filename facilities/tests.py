from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from accounts.models import User
from facilities.models import Room, Asset


class FacilitiesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username='mgr', password='Password123!', role=User.Role.MANAGER,
            is_first_login_2fa_completed=True, is_onboarding_completed=True
        )
        self.reporter = User.objects.create_user(
            username='rep', password='Password123!', role=User.Role.STUDENT,
            is_first_login_2fa_completed=True, is_onboarding_completed=True
        )
        self.room = Room.objects.create(
            building_name='Science Hall',
            building_code='SH',
            floor='1st',
            room_number='101',
            room_type=Room.RoomType.LECTURE_HALL,
            capacity=100
        )
        self.asset = Asset.objects.create(
            room=self.room,
            name='Ceiling Projector',
            asset_tag='AST-SH101-01',
            category=Asset.Category.AV_IT,
            status=Asset.Condition.OPERATIONAL
        )

    def test_room_unique_constraint(self):
        with self.assertRaises(IntegrityError):
            Room.objects.create(
                building_name='Different Science Hall',
                building_code='SH',
                floor='2nd',
                room_number='101',
                room_type=Room.RoomType.LAB,
                capacity=50
            )

    def test_asset_creation_and_cascade(self):
        self.assertEqual(self.room.assets.count(), 1)
        self.assertEqual(self.asset.room, self.room)
        self.room.delete()
        self.assertFalse(Asset.objects.filter(asset_tag='AST-SH101-01').exists())

    def test_room_assets_api(self):
        self.client.login(username='rep', password='Password123!')
        response = self.client.get(reverse('facilities:room_assets_api', args=[self.room.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('assets', data)
        self.assertEqual(len(data['assets']), 1)
        self.assertEqual(data['assets'][0]['tag'], 'AST-SH101-01')

    def test_room_creation_permissions(self):
        self.client.login(username='rep', password='Password123!')
        response = self.client.get(reverse('facilities:room_create'))
        self.assertEqual(response.status_code, 403)

        self.client.login(username='mgr', password='Password123!')
        response = self.client.get(reverse('facilities:room_create'))
        self.assertEqual(response.status_code, 200)
