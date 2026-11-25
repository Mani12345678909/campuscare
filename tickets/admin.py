from django.contrib import admin
from .models import MaintenanceRequest, TicketUpdate


class TicketUpdateInline(admin.TabularInline):
    model = TicketUpdate
    extra = 0
    readonly_fields = ('author', 'old_status', 'new_status', 'comment', 'created_at')
    can_delete = False


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_code',
        'title',
        'room',
        'category',
        'priority',
        'status',
        'reported_by',
        'assigned_to',
        'created_at',
    )
    list_filter = (
        'status',
        'priority',
        'category',
        'room__building_name',
        'created_at',
    )
    search_fields = (
        'ticket_code',
        'title',
        'description',
        'reported_by__username',
        'assigned_to__username',
        'room__room_number',
        'room__building_code',
    )
    readonly_fields = ('ticket_code', 'created_at', 'updated_at', 'resolved_at')
    inlines = [TicketUpdateInline]
    ordering = ('-created_at',)


@admin.register(TicketUpdate)
class TicketUpdateAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'old_status', 'new_status', 'created_at')
    list_filter = ('new_status', 'created_at')
    search_fields = ('ticket__ticket_code', 'comment', 'author__username')
    readonly_fields = ('ticket', 'author', 'old_status', 'new_status', 'comment', 'created_at')
    ordering = ('-created_at',)
