from django.db import models
from django.conf import settings
from django.utils import timezone
from facilities.models import Room, Asset


class MaintenanceRequest(models.Model):
    class ReportType(models.TextChoices):
        MAINTENANCE = 'MAINTENANCE', 'Classroom Equipment Repair'
        FACILITY_ISSUE = 'FACILITY_ISSUE', 'General Facility / Infrastructure'
        ACADEMIC_OPERATIONAL = 'ACADEMIC_OPERATIONAL', 'Academic / Lecture Operational Issue'

    class Category(models.TextChoices):
        ELECTRICAL = 'ELECTRICAL', 'Electrical'
        HVAC = 'HVAC', 'HVAC'
        AV_IT = 'AV_IT', 'AV / IT & Computing'
        FURNITURE = 'FURNITURE', 'Furniture'
        PLUMBING = 'PLUMBING', 'Plumbing'
        CLEANING = 'CLEANING', 'Cleaning & Sanitation'
        OTHER = 'OTHER', 'Other'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        TRIAGED = 'TRIAGED', 'Triaged'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        NEEDS_PARTS = 'NEEDS_PARTS', 'Needs Parts'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    ticket_code = models.CharField(max_length=30, unique=True, editable=False)
    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        default=ReportType.MAINTENANCE,
        db_index=True
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name='maintenance_requests'
    )
    asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_requests'
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reported_tickets'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets'
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True
    )
    issue_photo = models.ImageField(upload_to="tickets/%Y/%m/", null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            year = timezone.now().year
            prefix = f"CM-{year}-"
            last_record = MaintenanceRequest.objects.filter(
                ticket_code__startswith=prefix
            ).order_by('-ticket_code').first()

            if last_record and last_record.ticket_code:
                try:
                    num_part = last_record.ticket_code.split('-')[-1]
                    next_num = int(num_part) + 1
                except (ValueError, IndexError):
                    next_num = MaintenanceRequest.objects.filter(ticket_code__startswith=prefix).count() + 1
            else:
                next_num = 1

            self.ticket_code = f"{prefix}{next_num:04d}"

        # Automatic management of resolved_at timestamp
        if self.status in [self.Status.RESOLVED, self.Status.CLOSED]:
            if not self.resolved_at:
                self.resolved_at = timezone.now()
        else:
            if self.resolved_at:
                self.resolved_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_code}: {self.title} ({self.get_status_display()})"

    @property
    def is_open(self):
        return self.status not in [self.Status.RESOLVED, self.Status.CLOSED]


class TicketUpdate(models.Model):
    ticket = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name='updates'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ticket_updates'
    )
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, blank=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        author_name = self.author.username if self.author else "System"
        return f"Update on {self.ticket.ticket_code} by {author_name} at {self.created_at:%Y-%m-%d %H:%M}"
