from django.contrib import admin
from .models import (
    TimetableSlot,
    TeacherActivityLog,
    AttendanceSession,
    AttendanceRecord,
    ExamSchedule,
)


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ('student', 'status', 'remarks')


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = (
        'day_of_week',
        'period_number',
        'department',
        'year',
        'section',
        'subject_code',
        'faculty',
        'room',
        'status',
    )
    list_filter = ('day_of_week', 'department', 'year', 'section', 'status', 'room__building_name')
    search_fields = ('subject_name', 'subject_code', 'faculty__username', 'room__room_number')


@admin.register(TeacherActivityLog)
class TeacherActivityLogAdmin(admin.ModelAdmin):
    list_display = ('date', 'faculty', 'room', 'session_status', 'topic_covered', 'created_at')
    list_filter = ('session_status', 'date', 'faculty__department')
    search_fields = ('faculty__username', 'room__room_number', 'topic_covered')


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('timetable_slot', 'date', 'conducted_by', 'total_count', 'present_count')
    list_filter = ('date', 'timetable_slot__department', 'timetable_slot__section')
    search_fields = ('timetable_slot__subject_code', 'conducted_by__username')
    inlines = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('session', 'student', 'status', 'remarks')
    list_filter = ('status', 'session__date')
    search_fields = ('student__username', 'student__identifier_number')


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'exam_name',
        'subject_code',
        'department',
        'section',
        'exam_date',
        'start_time',
        'room',
        'invigilator',
        'room_readiness_checked',
    )
    list_filter = ('exam_date', 'department', 'room_readiness_checked', 'room__building_name')
    search_fields = ('exam_name', 'subject_name', 'subject_code', 'room__room_number')
