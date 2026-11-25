from django.shortcuts import render, redirect
from django.db.models import Count, Sum, Q
from django.utils import timezone
from tickets.models import MaintenanceRequest
from facilities.models import Room, Asset
from accounts.models import User
from academics.models import TimetableSlot, TeacherActivityLog, AttendanceRecord, ExamSchedule
from notices.models import Announcement, FeeRecord


def index_view(request):
    """
    Root view routing:
    - If logged in, routes to the role-aware dashboard.
    - If anonymous, renders an informative landing page with system capabilities and quick demo logins.
    """
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    return render(request, 'core/landing.html')


def dashboard_view(request):
    """
    Role-aware operational dashboard:
    - Students see attendance stats, today's schedule, fee dues, and reported tickets.
    - Faculty see their teaching schedule, quick attendance/activity logging, and exam invigilation.
    - Technicians see repair backlog and unassigned pool.
    - Managers & Admins see university-wide KPIs, hotspots, fee metrics, and quick report links.
    """
    if not request.user.is_authenticated:
        return redirect('core:index')

    user = request.user
    context = {'user': user}

    open_statuses = [
        MaintenanceRequest.Status.SUBMITTED,
        MaintenanceRequest.Status.TRIAGED,
        MaintenanceRequest.Status.ASSIGNED,
        MaintenanceRequest.Status.IN_PROGRESS,
        MaintenanceRequest.Status.NEEDS_PARTS,
    ]

    today_date = timezone.now().date()
    # Weekday code (MON, TUE, WED, THU, FRI, SAT, SUN)
    weekday_map = {0: 'MON', 1: 'TUE', 2: 'WED', 3: 'THU', 4: 'FRI', 5: 'SAT', 6: 'SUN'}
    today_code = weekday_map.get(today_date.weekday(), 'MON')

    # ================= STUDENT CONTEXT =================
    if user.is_student:
        my_tickets = MaintenanceRequest.objects.filter(
            reported_by=user
        ).select_related('room', 'asset', 'assigned_to').order_by('-created_at')

        # Attendance calculation
        st_records = AttendanceRecord.objects.filter(student=user)
        total_sessions = st_records.count()
        attended = st_records.filter(status__in=['PRESENT', 'ON_DUTY']).count()
        overall_attendance = round((attended / total_sessions) * 100, 1) if total_sessions > 0 else 0

        # Pending Fees
        pending_fee_sum = FeeRecord.objects.filter(
            student=user, status__in=['PENDING', 'OVERDUE']
        ).aggregate(s=Sum('amount'))['s'] or 0

        # Today's Timetable
        today_slots = TimetableSlot.objects.filter(
            day_of_week=today_code
        ).select_related('faculty', 'room').order_by('period_number')
        if user.department:
            dept_slots = today_slots.filter(department__icontains=user.department)
            if dept_slots.exists():
                today_slots = dept_slots

        # Upcoming Exams
        upcoming_exams = ExamSchedule.objects.filter(
            exam_date__gte=today_date
        ).select_related('room').order_by('exam_date')[:4]

        # Recent announcements
        recent_announcements = Announcement.objects.filter(
            Q(target_role__in=['ALL', 'STUDENT'])
        ).order_by('-is_pinned', '-created_at')[:4]

        context.update({
            'my_total_count': my_tickets.count(),
            'my_open_count': my_tickets.filter(status__in=open_statuses).count(),
            'my_resolved_count': my_tickets.filter(status__in=['RESOLVED', 'CLOSED']).count(),
            'recent_tickets': my_tickets[:6],
            'overall_attendance': overall_attendance,
            'is_low_attendance': overall_attendance < 75.0,
            'pending_fee_sum': pending_fee_sum,
            'today_slots': today_slots,
            'upcoming_exams': upcoming_exams,
            'recent_announcements': recent_announcements,
        })

    # ================= FACULTY CONTEXT =================
    elif user.is_faculty:
        # Today's teaching schedule
        my_today_slots = TimetableSlot.objects.filter(
            faculty=user,
            day_of_week=today_code
        ).select_related('room').order_by('period_number')

        # Recent logs
        recent_logs = TeacherActivityLog.objects.filter(
            faculty=user
        ).select_related('room', 'timetable_slot').order_by('-date')[:5]

        # Upcoming Invigilation
        my_exams = ExamSchedule.objects.filter(
            invigilator=user,
            exam_date__gte=today_date
        ).select_related('room').order_by('exam_date')[:4]

        my_tickets = MaintenanceRequest.objects.filter(
            reported_by=user
        ).select_related('room', 'asset').order_by('-created_at')[:5]

        context.update({
            'my_today_slots': my_today_slots,
            'recent_logs': recent_logs,
            'my_exams': my_exams,
            'recent_tickets': my_tickets,
            'today_code': today_code,
        })

    # ================= TECHNICIAN CONTEXT =================
    elif user.is_technician:
        my_assigned = MaintenanceRequest.objects.filter(
            assigned_to=user
        ).select_related('room', 'asset', 'reported_by').order_by('-priority', '-created_at')

        unassigned_pool = MaintenanceRequest.objects.filter(
            assigned_to__isnull=True,
            status__in=open_statuses
        ).select_related('room', 'asset', 'reported_by').order_by('-priority', '-created_at')[:8]

        context.update({
            'assigned_open_count': my_assigned.filter(status__in=open_statuses).count(),
            'in_progress_count': my_assigned.filter(status=MaintenanceRequest.Status.IN_PROGRESS).count(),
            'resolved_by_me_count': my_assigned.filter(status__in=[MaintenanceRequest.Status.RESOLVED, MaintenanceRequest.Status.CLOSED]).count(),
            'my_assigned_tickets': my_assigned[:10],
            'unassigned_pool': unassigned_pool,
        })

    # ================= MANAGER / ADMIN CONTEXT =================
    if user.is_manager or user.is_admin_role:
        all_tickets = MaintenanceRequest.objects.all()

        total_open = all_tickets.filter(status__in=open_statuses).count()
        critical_high_count = all_tickets.filter(
            status__in=open_statuses,
            priority__in=[MaintenanceRequest.Priority.CRITICAL, MaintenanceRequest.Priority.HIGH]
        ).count()
        resolved_count = all_tickets.filter(
            status__in=[MaintenanceRequest.Status.RESOLVED, MaintenanceRequest.Status.CLOSED]
        ).count()

        # Category Breakdown
        category_counts = (
            all_tickets.values('category')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        category_labels = dict(MaintenanceRequest.Category.choices)
        category_data = [
            {
                'category_code': item['category'],
                'category_name': category_labels.get(item['category'], item['category']),
                'count': item['total']
            }
            for item in category_counts
        ]

        # Top 5 recurring hotspot rooms
        recurring_rooms = (
            Room.objects.annotate(ticket_count=Count('maintenance_requests'))
            .filter(ticket_count__gt=0)
            .order_by('-ticket_count')[:5]
        )

        # Technician Workload
        technicians = (
            User.objects.filter(role=User.Role.TECHNICIAN)
            .annotate(
                open_assigned=Count(
                    'assigned_tickets',
                    filter=Q(assigned_tickets__status__in=open_statuses)
                ),
                total_resolved=Count(
                    'assigned_tickets',
                    filter=Q(assigned_tickets__status__in=[MaintenanceRequest.Status.RESOLVED, MaintenanceRequest.Status.CLOSED])
                )
            )
            .order_by('-open_assigned')
        )

        # Academic / Facility metrics
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_faculty = User.objects.filter(role=User.Role.FACULTY).count()
        total_rooms = Room.objects.filter(is_active=True).count()
        rooms_maintenance = Room.objects.filter(operational_status='MAINTENANCE').count()
        total_pending_fees = FeeRecord.objects.filter(status__in=['PENDING', 'OVERDUE']).aggregate(s=Sum('amount'))['s'] or 0

        # Requests needing triage
        triaged_needed = all_tickets.filter(
            status=MaintenanceRequest.Status.SUBMITTED
        ).select_related('room', 'asset', 'reported_by').order_by('-created_at')[:6]

        context.update({
            'total_open': total_open,
            'critical_high_count': critical_high_count,
            'resolved_count': resolved_count,
            'total_rooms': total_rooms,
            'rooms_maintenance': rooms_maintenance,
            'total_assets': Asset.objects.count(),
            'total_students': total_students,
            'total_faculty': total_faculty,
            'total_pending_fees': total_pending_fees,
            'category_data': category_data,
            'recurring_rooms': recurring_rooms,
            'technicians': technicians,
            'triaged_needed': triaged_needed,
        })

    return render(request, 'core/dashboard.html', context)
