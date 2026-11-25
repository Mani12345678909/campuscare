from django.db import models
from django.conf import settings
from facilities.models import Room


class TimetableSlot(models.Model):
    class DayOfWeek(models.TextChoices):
        MON = 'MON', 'Monday'
        TUE = 'TUE', 'Tuesday'
        WED = 'WED', 'Wednesday'
        THU = 'THU', 'Thursday'
        FRI = 'FRI', 'Friday'
        SAT = 'SAT', 'Saturday'

    class SlotStatus(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular Class'
        SUBSTITUTED = 'SUBSTITUTED', 'Substituted Faculty'
        RESCHEDULED = 'RESCHEDULED', 'Rescheduled'
        CANCELLED = 'CANCELLED', 'Cancelled'

    department = models.CharField(max_length=120)
    year = models.CharField(max_length=50, default='3rd Year')
    section = models.CharField(max_length=20, default='Section A')
    day_of_week = models.CharField(max_length=10, choices=DayOfWeek.choices, db_index=True)
    period_number = models.PositiveIntegerField(default=1)
    start_time = models.TimeField()
    end_time = models.TimeField()

    subject_name = models.CharField(max_length=150)
    subject_code = models.CharField(max_length=30)
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='teaching_slots'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='timetable_slots'
    )
    status = models.CharField(
        max_length=20,
        choices=SlotStatus.choices,
        default=SlotStatus.REGULAR
    )
    notes = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['day_of_week', 'period_number']

    def __str__(self):
        faculty_name = self.faculty.get_full_name() if self.faculty else "TBA"
        return f"{self.get_day_of_week_display()} P{self.period_number}: {self.subject_code} - {self.room.building_code} {self.room.room_number} ({faculty_name})"


class TeacherActivityLog(models.Model):
    class SessionStatus(models.TextChoices):
        CONDUCTED = 'CONDUCTED', 'Conducted (Regular)'
        SUBSTITUTED = 'SUBSTITUTED', 'Conducted as Substitute'
        CANCELLED = 'CANCELLED', 'Cancelled'
        LAB_HELD = 'LAB_HELD', 'Practical Lab Held'

    timetable_slot = models.ForeignKey(
        TimetableSlot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    date = models.DateField(db_index=True)
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='activity_logs'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='activity_logs'
    )
    topic_covered = models.TextField(help_text="Key lecture or practical topics covered.")
    session_status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.CONDUCTED
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Log: {self.date} - {self.faculty.username} - {self.room.room_number}"


class AttendanceSession(models.Model):
    timetable_slot = models.ForeignKey(
        TimetableSlot,
        on_delete=models.PROTECT,
        related_name='attendance_sessions'
    )
    date = models.DateField(db_index=True)
    conducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='conducted_attendances'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['timetable_slot', 'date'],
                name='unique_attendance_session_slot_date'
            )
        ]

    def __str__(self):
        return f"Attendance: {self.timetable_slot.subject_code} ({self.timetable_slot.section}) on {self.date}"

    @property
    def total_count(self):
        return self.records.count()

    @property
    def present_count(self):
        return self.records.filter(status='PRESENT').count()


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'
        ON_DUTY = 'ON_DUTY', 'On Duty (OD)'

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name='records'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='attendance_records'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT,
        db_index=True
    )
    remarks = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ['student__username']
        constraints = [
            models.UniqueConstraint(
                fields=['session', 'student'],
                name='unique_session_student_attendance'
            )
        ]

    def __str__(self):
        return f"{self.student.username}: {self.status}"


class ExamSchedule(models.Model):
    exam_name = models.CharField(max_length=120)
    subject_name = models.CharField(max_length=150)
    subject_code = models.CharField(max_length=30)
    department = models.CharField(max_length=120)
    year = models.CharField(max_length=50)
    section = models.CharField(max_length=20)
    exam_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='exam_schedules'
    )
    invigilator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invigilated_exams'
    )
    room_readiness_checked = models.BooleanField(
        default=False,
        help_text="Verification that room facilities (lighting, seats, AC/ventilation) are ready."
    )

    class Meta:
        ordering = ['exam_date', 'start_time']

    def __str__(self):
        return f"{self.exam_name}: {self.subject_code} ({self.room.building_code} {self.room.room_number}) on {self.exam_date}"

    @property
    def has_room_critical_issues(self):
        """Checks if the allocated exam hall has unresolved critical/high maintenance requests."""
        return self.room.has_critical_maintenance
