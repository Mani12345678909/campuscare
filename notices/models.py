from django.db import models
from django.conf import settings


class Announcement(models.Model):
    class Type(models.TextChoices):
        GENERAL = 'GENERAL', 'General Announcement'
        EVENT = 'EVENT', 'Campus Event'
        FEE_NOTICE = 'FEE_NOTICE', 'Fee / Financial Notice'
        EXAM_UPDATE = 'EXAM_UPDATE', 'Exam Schedule Update'
        MAINTENANCE_ALERT = 'MAINTENANCE_ALERT', 'Maintenance / Facility Alert'

    class TargetRole(models.TextChoices):
        ALL = 'ALL', 'All Campus Members'
        STUDENT = 'STUDENT', 'Students Only'
        FACULTY = 'FACULTY', 'Faculty Only'
        STAFF = 'STAFF', 'Facilities & Technical Staff'

    title = models.CharField(max_length=200)
    summary = models.CharField(max_length=300)
    body = models.TextField()
    announcement_type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.GENERAL,
        db_index=True
    )
    target_role = models.CharField(
        max_length=20,
        choices=TargetRole.choices,
        default=TargetRole.ALL,
        db_index=True
    )
    target_department = models.CharField(max_length=120, blank=True)
    event_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='announcements'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"[{self.get_announcement_type_display()}] {self.title}"


class FeeRecord(models.Model):
    class Status(models.TextChoices):
        PAID = 'PAID', 'Paid'
        PENDING = 'PENDING', 'Pending Due'
        OVERDUE = 'OVERDUE', 'Overdue'
        SCHOLARSHIP = 'SCHOLARSHIP', 'Scholarship Waived'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='fee_records'
    )
    academic_term = models.CharField(max_length=80, help_text="e.g. Fall 2026 - Semester 5")
    fee_category = models.CharField(max_length=120, help_text="e.g. Tuition & Lab Fee, Hostel Fee")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    paid_date = models.DateField(null=True, blank=True)
    receipt_number = models.CharField(max_length=60, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['due_date', 'status']

    def __str__(self):
        return f"{self.student.username} - {self.fee_category} (${self.amount}) - {self.get_status_display()}"
