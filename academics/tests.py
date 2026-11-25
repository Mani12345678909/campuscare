from datetime import date, time
from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from accounts.models import User
from facilities.models import Room
from academics.models import (
    TimetableSlot,
    TeacherActivityLog,
    AttendanceSession,
    AttendanceRecord,
    ExamSchedule,
)
from tickets.models import MaintenanceRequest


class AcademicsModuleTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.faculty = User.objects.create_user(
            username='prof_adams',
            email='adams@college.edu',
            password='Password123!',
            role=User.Role.FACULTY,
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.student = User.objects.create_user(
            username='student_bob',
            email='bob@college.edu',
            password='Password123!',
            role=User.Role.STUDENT,
            identifier_number='21CS010',
            department='Computer Science',
            is_first_login_2fa_completed=True,
            is_onboarding_completed=True
        )
        self.room = Room.objects.create(
            building_name='Alan Turing Hall',
            building_code='TAH',
            floor='3rd',
            room_number='301',
            room_type=Room.RoomType.CLASSROOM,
            capacity=60
        )
        self.slot = TimetableSlot.objects.create(
            department='Computer Science',
            year='3rd Year',
            section='Section A',
            day_of_week='MON',
            period_number=1,
            start_time=time(9, 0),
            end_time=time(9, 50),
            subject_name='Operating Systems',
            subject_code='CS302',
            faculty=self.faculty,
            room=self.room
        )

    def test_duplicate_attendance_session_prevention(self):
        test_date = date(2026, 11, 23)
        AttendanceSession.objects.create(
            timetable_slot=self.slot,
            date=test_date,
            conducted_by=self.faculty
        )

        # Attempting duplicate session for same slot + date must raise IntegrityError
        with self.assertRaises(IntegrityError):
            AttendanceSession.objects.create(
                timetable_slot=self.slot,
                date=test_date,
                conducted_by=self.faculty
            )

    def test_attendance_recording_and_percentage_calculation(self):
        # Create 4 sessions for the slot
        dates = [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 4)]
        for idx, d in enumerate(dates):
            sess = AttendanceSession.objects.create(
                timetable_slot=self.slot, date=d, conducted_by=self.faculty
            )
            # Bob is present 3 times out of 4 (75%)
            status = AttendanceRecord.Status.PRESENT if idx < 3 else AttendanceRecord.Status.ABSENT
            AttendanceRecord.objects.create(session=sess, student=self.student, status=status)

        # Check records
        records = AttendanceRecord.objects.filter(student=self.student)
        self.assertEqual(records.count(), 4)
        attended = records.filter(status='PRESENT').count()
        self.assertEqual(attended, 3)
        pct = (attended / 4) * 100
        self.assertEqual(pct, 75.0)

        # Student accesses attendance view
        self.client.login(username='student_bob', password='Password123!')
        response = self.client.get(reverse('academics:attendance_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '75.0%')
        self.assertContains(response, 'Operating Systems')

    def test_teacher_activity_log_creation(self):
        self.client.login(username='prof_adams', password='Password123!')
        response = self.client.post(reverse('academics:activity_log_create'), {
            'timetable_slot': self.slot.id,
            'date': '2026-11-22',
            'room': self.room.id,
            'session_status': TeacherActivityLog.SessionStatus.CONDUCTED,
            'topic_covered': 'Virtual Memory, Page Replacement Algorithms (LRU, FIFO)',
            'remarks': 'Lab demo conducted successfully.',
        })
        self.assertEqual(response.status_code, 302)
        log = TeacherActivityLog.objects.get(topic_covered__contains='Virtual Memory')
        self.assertEqual(log.faculty, self.faculty)
        self.assertEqual(log.room, self.room)

    def test_exam_room_readiness_flagging(self):
        exam = ExamSchedule.objects.create(
            exam_name='Semester Theory Exam',
            subject_name='Operating Systems',
            subject_code='CS302',
            department='Computer Science',
            year='3rd Year',
            section='Section A',
            exam_date=date(2026, 12, 10),
            start_time=time(10, 0),
            end_time=time(13, 0),
            room=self.room,
            invigilator=self.faculty
        )
        # Initially, room has no critical tickets
        self.assertFalse(exam.has_room_critical_issues)

        # Create critical maintenance ticket in this room
        MaintenanceRequest.objects.create(
            room=self.room,
            reported_by=self.student,
            title='Ceiling fan short circuit',
            description='Electrical spark hazard.',
            priority=MaintenanceRequest.Priority.CRITICAL,
            status=MaintenanceRequest.Status.SUBMITTED
        )

        # Now room readiness check must flag critical issue!
        self.assertTrue(exam.has_room_critical_issues)
