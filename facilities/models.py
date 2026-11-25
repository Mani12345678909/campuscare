from django.db import models


class Room(models.Model):
    class RoomType(models.TextChoices):
        CLASSROOM = 'Classroom', 'Classroom'
        LECTURE_HALL = 'Lecture Hall', 'Lecture Hall'
        LAB = 'Lab', 'Lab'
        SEMINAR_HALL = 'Seminar Hall', 'Seminar Hall'

    class OperationalStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        OCCUPIED = 'OCCUPIED', 'Occupied (In Session)'
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'
        RESERVED = 'RESERVED', 'Reserved (Exam/Event)'

    building_name = models.CharField(max_length=120)
    building_code = models.CharField(max_length=20)
    floor = models.CharField(max_length=20)
    room_number = models.CharField(max_length=20)
    room_type = models.CharField(
        max_length=50,
        choices=RoomType.choices,
        default=RoomType.CLASSROOM
    )
    capacity = models.PositiveIntegerField(default=30)
    operational_status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.AVAILABLE,
        db_index=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['building_code', 'room_number']
        constraints = [
            models.UniqueConstraint(
                fields=['building_code', 'room_number'],
                name='unique_building_room'
            )
        ]

    def __str__(self):
        return f"{self.building_code} {self.room_number} - {self.building_name} ({self.room_type})"

    @property
    def has_critical_maintenance(self):
        """
        Flags if this room has active high/critical maintenance tickets or is marked MAINTENANCE.
        Used for exam/event readiness validation.
        """
        if self.operational_status == self.OperationalStatus.MAINTENANCE:
            return True
        return self.maintenance_requests.filter(
            status__in=['SUBMITTED', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'NEEDS_PARTS'],
            priority__in=['HIGH', 'CRITICAL']
        ).exists()


class Asset(models.Model):
    class Condition(models.TextChoices):
        OPERATIONAL = 'OPERATIONAL', 'Operational (Good)'
        NEEDS_REPAIR = 'NEEDS_REPAIR', 'Needs Repair'
        OUT_OF_SERVICE = 'OUT_OF_SERVICE', 'Out of Service'

    # Alias for backward compatibility
    Status = Condition

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='assets'
    )
    name = models.CharField(max_length=150)
    asset_tag = models.CharField(max_length=60, unique=True)
    category = models.CharField(
        max_length=20,
        choices=[
            ('ELECTRICAL', 'Electrical'),
            ('HVAC', 'HVAC'),
            ('AV_IT', 'AV / IT'),
            ('FURNITURE', 'Furniture'),
            ('PLUMBING', 'Plumbing'),
            ('CLEANING', 'Cleaning'),
            ('OTHER', 'Other'),
        ],
        default='OTHER'
    )
    status = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.OPERATIONAL
    )
    installed_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['room', 'name']

    def __str__(self):
        return f"{self.name} [{self.asset_tag}] ({self.room.building_code} {self.room.room_number})"

    class Category(models.TextChoices):
        ELECTRICAL = 'ELECTRICAL', 'Electrical'
        HVAC = 'HVAC', 'HVAC'
        AV_IT = 'AV_IT', 'AV / IT'
        FURNITURE = 'FURNITURE', 'Furniture'
        PLUMBING = 'PLUMBING', 'Plumbing'
        CLEANING = 'CLEANING', 'Cleaning'
        OTHER = 'OTHER', 'Other'
