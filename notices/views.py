import csv
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Q
from .models import Announcement, FeeRecord
from .forms import AnnouncementForm, FeeRecordForm
from tickets.models import MaintenanceRequest, TicketUpdate
from facilities.models import Room
from academics.models import TimetableSlot, TeacherActivityLog, AttendanceSession, AttendanceRecord, ExamSchedule
from accounts.models import User
from accounts.permissions import manager_required


@login_required
def announcement_list_view(request):
    if request.user.is_authenticated:
        request.user.mark_feature_visited('notices')

    type_filter = request.GET.get('type', '')
    announcements = Announcement.objects.select_related('created_by').order_by('-is_pinned', '-created_at')

    if type_filter:
        announcements = announcements.filter(announcement_type=type_filter)

    # Filter target roles for regular students or staff
    user = request.user
    if not (user.is_manager or user.is_admin_role):
        role_q = Q(target_role=Announcement.TargetRole.ALL)
        if user.is_student:
            role_q |= Q(target_role=Announcement.TargetRole.STUDENT)
        elif user.is_faculty:
            role_q |= Q(target_role=Announcement.TargetRole.FACULTY)
        elif user.is_technician:
            role_q |= Q(target_role=Announcement.TargetRole.STAFF)
        announcements = announcements.filter(role_q)

    return render(request, 'notices/announcement_list.html', {
        'announcements': announcements,
        'type_filter': type_filter,
        'types': Announcement.Type.choices,
    })


@login_required
def announcement_detail_view(request, announcement_id):
    if request.user.is_authenticated:
        request.user.mark_feature_visited('notices')

    announcement = get_object_or_404(Announcement.objects.select_related('created_by'), pk=announcement_id)
    return render(request, 'notices/announcement_detail.html', {
        'announcement': announcement,
    })


@login_required
@manager_required
def announcement_create_view(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            messages.success(request, f"Notice '{announcement.title}' posted successfully.")
            return redirect('notices:announcement_list')
    else:
        form = AnnouncementForm()

    return render(request, 'notices/announcement_form.html', {'form': form})


@login_required
def fee_tracker_view(request):
    user = request.user
    status_filter = request.GET.get('status', '')

    if user.is_student:
        records = FeeRecord.objects.filter(student=user).order_by('due_date')
        if status_filter:
            records = records.filter(status=status_filter)

        total_due = records.filter(status__in=['PENDING', 'OVERDUE']).aggregate(s=Sum('amount'))['s'] or 0
        total_paid = records.filter(status='PAID').aggregate(s=Sum('amount'))['s'] or 0

        return render(request, 'notices/fee_student.html', {
            'records': records,
            'total_due': total_due,
            'total_paid': total_paid,
            'status_filter': status_filter,
        })

    # Manager / Admin view
    records = FeeRecord.objects.select_related('student').order_by('due_date', 'status')
    if status_filter:
        records = records.filter(status=status_filter)

    total_collected = FeeRecord.objects.filter(status='PAID').aggregate(s=Sum('amount'))['s'] or 0
    total_pending = FeeRecord.objects.filter(status='PENDING').aggregate(s=Sum('amount'))['s'] or 0
    total_overdue = FeeRecord.objects.filter(status='OVERDUE').aggregate(s=Sum('amount'))['s'] or 0

    return render(request, 'notices/fee_manager.html', {
        'records': records,
        'total_collected': total_collected,
        'total_pending': total_pending,
        'total_overdue': total_overdue,
        'status_filter': status_filter,
        'statuses': FeeRecord.Status.choices,
    })


@login_required
@manager_required
def fee_create_view(request):
    if request.method == 'POST':
        form = FeeRecordForm(request.POST)
        if form.is_valid():
            fee = form.save()
            messages.success(request, f"Fee record created for {fee.student.username}.")
            return redirect('notices:fee_tracker')
    else:
        form = FeeRecordForm()

    return render(request, 'notices/fee_form.html', {'form': form})


@login_required
def live_feed_view(request):
    """
    Unified Activity & Watch Feed:
    Aggregates recent maintenance updates, room readiness, announcements,
    timetable substitutions, and exam events in unified chronological order.
    """
    category_filter = request.GET.get('cat', 'ALL')
    feed_items = []

    # 1. Maintenance updates
    if category_filter in ['ALL', 'MAINTENANCE']:
        updates = TicketUpdate.objects.select_related('ticket__room', 'author').order_by('-created_at')[:15]
        for u in updates:
            feed_items.append({
                'category': 'MAINTENANCE',
                'badge_class': 'bg-warning text-dark',
                'icon': 'bi-wrench',
                'title': f"Ticket #{u.ticket.ticket_code}: {u.ticket.title}",
                'meta': f"Room {u.ticket.room.building_code} {u.ticket.room.room_number} &bull; Author: {u.author.username if u.author else 'System'}",
                'body': f"Status transitioned to {u.new_status or u.ticket.status}. Note: {u.comment}",
                'timestamp': u.created_at,
                'link': f"/tickets/{u.ticket.ticket_code}/",
            })

    # 2. Announcements & Events
    if category_filter in ['ALL', 'EVENTS']:
        announcements = Announcement.objects.select_related('created_by').order_by('-created_at')[:15]
        for a in announcements:
            feed_items.append({
                'category': 'EVENTS',
                'badge_class': 'bg-info text-white',
                'icon': 'bi-megaphone',
                'title': f"{a.get_announcement_type_display()}: {a.title}",
                'meta': f"Audience: {a.get_target_role_display()} &bull; Posted by {a.created_by.username if a.created_by else 'Admin'}",
                'body': a.summary,
                'timestamp': a.created_at,
                'link': f"/notices/announcements/{a.id}/",
            })

    # 3. Timetable substitutions / reschedules
    if category_filter in ['ALL', 'ACADEMICS']:
        slots = TimetableSlot.objects.filter(~Q(status='REGULAR')).select_related('faculty', 'room')[:10]
        for s in slots:
            feed_items.append({
                'category': 'ACADEMICS',
                'badge_class': 'bg-primary text-white',
                'icon': 'bi-calendar3',
                'title': f"Timetable Alert: {s.subject_code} - {s.get_status_display()}",
                'meta': f"{s.get_day_of_week_display()} P{s.period_number} &bull; Room {s.room.building_code} {s.room.room_number}",
                'body': f"Subject: {s.subject_name}. Faculty: {s.faculty.get_full_name() if s.faculty else 'TBA'}. {s.notes}",
                'timestamp': timezone.now(),
                'link': "/academics/timetable/",
            })

    # 4. Exam Schedules
    if category_filter in ['ALL', 'EXAMS']:
        exams = ExamSchedule.objects.select_related('room', 'invigilator').order_by('exam_date')[:10]
        for e in exams:
            readiness_str = "Verified Ready" if e.room_readiness_checked else "Readiness Check Pending"
            has_crit = e.has_room_critical_issues
            feed_items.append({
                'category': 'EXAMS',
                'badge_class': 'bg-danger text-white' if has_crit else 'bg-dark text-white',
                'icon': 'bi-mortarboard',
                'title': f"Exam Notice: {e.exam_name} ({e.subject_code})",
                'meta': f"Date: {e.exam_date} &bull; Room: {e.room.building_code} {e.room.room_number} &bull; {readiness_str}",
                'body': f"Department: {e.department} ({e.section}). {'CRITICAL: Room has active maintenance tickets!' if has_crit else ''}",
                'timestamp': timezone.now(),
                'link': "/academics/exams/",
            })

    # Sort items chronologically descending
    feed_items.sort(key=lambda x: x['timestamp'], reverse=True)

    return render(request, 'notices/live_feed.html', {
        'feed_items': feed_items[:30],
        'category_filter': category_filter,
    })


@login_required
def reports_hub_view(request):
    """
    Reporting dashboard hub with summary metrics and one-click CSV export options.
    """
    total_tickets = MaintenanceRequest.objects.count()
    open_tickets = MaintenanceRequest.objects.exclude(status__in=['RESOLVED', 'CLOSED']).count()
    total_attendance_sessions = AttendanceSession.objects.count()
    total_activity_logs = TeacherActivityLog.objects.count()

    top_recurring_rooms = Room.objects.annotate(
        ticket_count=Count('maintenance_requests')
    ).filter(ticket_count__gt=0).order_by('-ticket_count')[:5]

    return render(request, 'notices/reports_hub.html', {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'total_attendance_sessions': total_attendance_sessions,
        'total_activity_logs': total_activity_logs,
        'top_recurring_rooms': top_recurring_rooms,
    })


# ================= CSV EXPORT ENDPOINTS =================

@login_required
def export_maintenance_csv(request):
    """
    Export (1): Maintenance & Recurring Room Faults Report CSV.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="maintenance_room_faults_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Ticket Code', 'Title', 'Report Type', 'Building', 'Room Number', 'Asset Tag',
        'Asset Name', 'Category', 'Priority', 'Status', 'Reported By',
        'Assigned To', 'Created Date', 'Resolved Date', 'Resolution Notes'
    ])

    tickets = MaintenanceRequest.objects.select_related(
        'room', 'asset', 'reported_by', 'assigned_to'
    ).order_by('-created_at')

    for t in tickets:
        writer.writerow([
            t.ticket_code,
            t.title,
            t.get_report_type_display(),
            t.room.building_name,
            f"{t.room.building_code} {t.room.room_number}",
            t.asset.asset_tag if t.asset else 'N/A',
            t.asset.name if t.asset else 'N/A',
            t.get_category_display(),
            t.get_priority_display(),
            t.get_status_display(),
            t.reported_by.username,
            t.assigned_to.username if t.assigned_to else 'Unassigned',
            t.created_at.strftime('%Y-%m-%d %H:%M'),
            t.resolved_at.strftime('%Y-%m-%d %H:%M') if t.resolved_at else '',
            t.resolution_notes.replace('\n', ' ') if t.resolution_notes else ''
        ])

    return response


@login_required
def export_attendance_csv(request):
    """
    Export (2): Attendance Summary Report CSV.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_attendance_summary_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Student Username', 'Roll / ID', 'Full Name', 'Department',
        'Subject Code', 'Subject Name', 'Total Sessions Held',
        'Attended Sessions', 'Attendance Percentage', 'Status Flag'
    ])

    students = User.objects.filter(role=User.Role.STUDENT).order_by('department', 'identifier_number')
    subjects = TimetableSlot.objects.values('subject_code', 'subject_name').distinct()

    for student in students:
        for subj in subjects:
            s_code = subj['subject_code']
            s_name = subj['subject_name']
            records = AttendanceRecord.objects.filter(
                student=student,
                session__timetable_slot__subject_code=s_code
            )
            total = records.count()
            if total > 0:
                attended = records.filter(status__in=['PRESENT', 'ON_DUTY']).count()
                pct = round((attended / total) * 100, 1)
                flag = 'CRITICAL (<75%)' if pct < 75.0 else 'GOOD'
                writer.writerow([
                    student.username,
                    student.identifier_number,
                    student.get_full_name(),
                    student.department,
                    s_code,
                    s_name,
                    total,
                    attended,
                    f"{pct}%",
                    flag
                ])

    return response


@login_required
def export_teacher_activity_csv(request):
    """
    Export (3): Teacher Activity & Class Log Report CSV.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="teacher_activity_class_log_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Log ID', 'Date', 'Faculty Username', 'Faculty Name', 'Department',
        'Room', 'Subject Code', 'Section', 'Session Status', 'Topic Covered', 'Remarks'
    ])

    logs = TeacherActivityLog.objects.select_related(
        'faculty', 'room', 'timetable_slot'
    ).order_by('-date')

    for log in logs:
        writer.writerow([
            log.id,
            log.date.strftime('%Y-%m-%d'),
            log.faculty.username,
            log.faculty.get_full_name(),
            log.faculty.department,
            f"{log.room.building_code} {log.room.room_number}",
            log.timetable_slot.subject_code if log.timetable_slot else 'Ad-hoc',
            log.timetable_slot.section if log.timetable_slot else '',
            log.get_session_status_display(),
            log.topic_covered.replace('\n', ' '),
            log.remarks.replace('\n', ' ')
        ])

    return response
