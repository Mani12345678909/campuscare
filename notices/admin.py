from django.contrib import admin
from .models import Announcement, FeeRecord


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'announcement_type', 'target_role', 'event_date', 'due_date', 'is_pinned', 'created_at')
    list_filter = ('announcement_type', 'target_role', 'is_pinned', 'created_at')
    search_fields = ('title', 'summary', 'body')


@admin.register(FeeRecord)
class FeeRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'academic_term', 'fee_category', 'amount', 'due_date', 'status', 'paid_date')
    list_filter = ('status', 'academic_term', 'due_date')
    search_fields = ('student__username', 'student__identifier_number', 'receipt_number')
