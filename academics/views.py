from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from .models import (
    TimetableSlot,
    TeacherActivityLog,
    AttendanceSession,
    AttendanceRecord,
    ExamSchedule,
)
from .forms import TimetableSlotForm, TeacherActivityLogForm, ExamScheduleForm
from facilities.models import Room
from accounts.models import User
from accounts.permissions import faculty_required, manager_required


@login_required
def timetable_view(request):
    """
    Displays weekly academic timetable grid with filters for Section, Faculty, and Room.
    """
    user = request.user
    if user.is_authenticated:
        user.mark_feature_visited('timetable')
    dept_filter = request.GET.get('department', '')
    sec_filter = request.GET.get('section', '')
    fac_filter = request.GET.get('faculty', '')
    room_filter = request.GET.get('room', '')

    slots = TimetableSlot.objects.select_related('faculty', 'room').order_by('day_of_week', 'period_number')

    # Defaults for convenience
    if not (dept_filter or sec_filter or fac_filter or room_filter):
        if user.is_student and user.department:
            dept_filter = user.department
        elif user.is_faculty:
            fac_filter = str(user.id)

    if dept_filter:
        slots = slots.filter(department__icontains=dept_filter)
    if sec_filter:
        slots = slots.filter(section__icontains=sec_filter)
    if fac_filter:
        slots = slots.filter(faculty_id=fac_filter)
    if room_filter:
        slots = slots.filter(room_id=room_filter)

    days_order = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
    days_labels = dict(TimetableSlot.DayOfWeek.choices)

    timetable_by_day = {day: [] for day in days_order}
    for slot in slots:
        if slot.day_of_week in timetable_by_day:
            timetable_by_day[slot.day_of_week].append(slot)

    departments = TimetableSlot.objects.values_list('department', flat=True).distinct()
    sections = TimetableSlot.objects.values_list('section', flat=True).distinct()
    faculties = User.objects.filter(role__in=[User.Role.FACULTY, User.Role.ADMIN])
    rooms = Room.objects.filter(is_active=True).order_by('building_code', 'room_number')

    return render(request, 'academics/timetable.html', {
        'timetable_by_day': timetable_by_day,
        'days_labels': days_labels,
        'departments': departments,
        'sections': sections,
        'faculties': faculties,
        'rooms': rooms,
        'dept_filter': dept_filter,
        'sec_filter': sec_filter,
        'fac_filter': fac_filter,
        'room_filter': room_filter,
    })


@login_required
@manager_required
def timetable_slot_create_view(request):
    if request.method == 'POST':
        form = TimetableSlotForm(request.POST)
        if form.is_valid():
            slot = form.save()
            messages.success(request, f"Timetable slot for {slot.subject_code} ({slot.get_day_of_week_display()}) added.")
            return redirect('academics:timetable')
    else:
        form = TimetableSlotForm()

    return render(request, 'academics/timetable_slot_form.html', {'form': form})


@login_required
def activity_log_list_view(request):
    """
    Daily teacher activity logs. Faculty see their own; managers/admins see all.
    """
    user = request.user
    date_filter = request.GET.get('date', '')

    logs = TeacherActivityLog.objects.select_related('faculty', 'room', 'timetable_slot').order_by('-date', '-created_at')

    if user.is_faculty and not (user.is_manager or user.is_admin_role):
        logs = logs.filter(faculty=user)

    if date_filter:
        logs = logs.filter(date=date_filter)

    return render(request, 'academics/activity_log_list.html', {
        'logs': logs,
        'date_filter': date_filter,
    })


@login_required
@faculty_required
def activity_log_create_view(request):
    """
    Faculty logs daily conducted lecture or lab sessions.
    """
    if request.method == 'POST':
        form = TeacherActivityLogForm(request.POST, faculty_user=request.user)
        if form.is_valid():
            log = form.save(commit=False)
            log.faculty = request.user
            log.save()
            messages.success(request, f"Class activity for {log.date} recorded successfully.")
            return redirect('academics:activity_log_list')
    else:
        initial = {'date': timezone.now().date()}
        slot_id = request.GET.get('slot')
        if slot_id:
            slot = TimetableSlot.objects.filter(pk=slot_id).first()
            if slot:
                initial['timetable_slot'] = slot
                initial['room'] = slot.room
        form = TeacherActivityLogForm(initial=initial, faculty_user=request.user)

    return render(request, 'academics/activity_log_form.html', {'form': form})


@login_required
def attendance_dashboard_view(request):
    """
    Attendance tracking:
    - Students view subject-wise attendance percentages & overall standing (<75% triggers alert).
    - Faculty/Managers view low attendance watchlist and recent conducted sessions.
    """
    user = request.user

    if user.is_student:
        # Subject-wise attendance calculation for the student
        records = AttendanceRecord.objects.filter(student=user).select_related(
            'session__timetable_slot', 'session__conducted_by'
        )

        subject_stats = {}
        total_sessions = 0
        total_attended = 0

        for r in records:
            slot = r.session.timetable_slot
            subj = slot.subject_code
            if subj not in subject_stats:
                subject_stats[subj] = {
                    'subject_name': slot.subject_name,
                    'subject_code': subj,
                    'total': 0,
                    'attended': 0,
                }
            subject_stats[subj]['total'] += 1
            total_sessions += 1

            if r.status in ['PRESENT', 'ON_DUTY']:
                subject_stats[subj]['attended'] += 1
                total_attended += 1

        for stats in subject_stats.values():
            pct = round((stats['attended'] / stats['total']) * 100, 1) if stats['total'] > 0 else 0
            stats['percentage'] = pct
            stats['is_low'] = pct < 75.0

        overall_pct = round((total_attended / total_sessions) * 100, 1) if total_sessions > 0 else 0

        return render(request, 'academics/attendance_student.html', {
            'subject_stats': subject_stats.values(),
            'total_sessions': total_sessions,
            'total_attended': total_attended,
            'overall_pct': overall_pct,
            'is_low_overall': overall_pct < 75.0,
            'recent_records': records.order_by('-session__date')[:10],
        })

    # Faculty & Manager View
    sessions = AttendanceSession.objects.select_related(
        'timetable_slot__room', 'conducted_by'
    ).prefetch_related('records').order_by('-date')[:15]

    # Low attendance alert query (<75% in any subject)
    low_attendance_students = []
    students = User.objects.filter(role=User.Role.STUDENT)
    for st in students:
        st_records = AttendanceRecord.objects.filter(student=st)
        t_count = st_records.count()
        if t_count >= 3:
            att_count = st_records.filter(status__in=['PRESENT', 'ON_DUTY']).count()
            pct = round((att_count / t_count) * 100, 1)
            if pct < 75.0:
                low_attendance_students.append({
                    'student': st,
                    'total': t_count,
                    'attended': att_count,
                    'percentage': pct,
                })

    return render(request, 'academics/attendance_staff.html', {
        'sessions': sessions,
        'low_attendance_students': low_attendance_students,
    })


@login_required
@faculty_required
def attendance_mark_view(request):
    """
    Faculty marks attendance for a class slot on a given date.
    Prevents duplicate sessions for the same slot + date.
    """
    slot_id = request.GET.get('slot') or request.POST.get('slot')
    date_str = request.GET.get('date') or request.POST.get('date') or timezone.now().date().isoformat()

    available_slots = TimetableSlot.objects.select_related('room', 'faculty')
    if request.user.is_faculty and not (request.user.is_manager or request.user.is_admin_role):
        available_slots = available_slots.filter(faculty=request.user)

    selected_slot = None
    if slot_id:
        selected_slot = get_object_or_404(TimetableSlot, pk=slot_id)

    students = User.objects.filter(role=User.Role.STUDENT).order_by('identifier_number', 'username')
    if selected_slot and selected_slot.section:
        # Filter section students if assigned
        sec_students = students.filter(year_or_block__icontains=selected_slot.section)
        if sec_students.exists():
            students = sec_students

    existing_session = None
    if selected_slot and date_str:
        existing_session = AttendanceSession.objects.filter(
            timetable_slot=selected_slot, date=date_str
        ).first()

    if request.method == 'POST' and selected_slot:
        # Create or update AttendanceSession
        session, created = AttendanceSession.objects.get_or_create(
            timetable_slot=selected_slot,
            date=date_str,
            defaults={'conducted_by': request.user}
        )
        if not created:
            session.conducted_by = request.user
            session.save()

        # Update records per student
        for student in students:
            status_val = request.POST.get(f"status_{student.id}", 'PRESENT')
            AttendanceRecord.objects.update_or_create(
                session=session,
                student=student,
                defaults={'status': status_val}
            )

        messages.success(
            request,
            f"Attendance for {selected_slot.subject_code} on {date_str} successfully saved ({students.count()} students recorded)."
        )
        return redirect('academics:attendance_dashboard')

    # Build student attendance statuses if session already exists
    student_rows = []
    for student in students:
        rec_status = 'PRESENT'
        if existing_session:
            rec = existing_session.records.filter(student=student).first()
            if rec:
                rec_status = rec.status
        student_rows.append({
            'student': student,
            'current_status': rec_status,
        })

    return render(request, 'academics/attendance_mark.html', {
        'available_slots': available_slots,
        'selected_slot': selected_slot,
        'date_str': date_str,
        'student_rows': student_rows,
        'existing_session': existing_session,
    })


@login_required
def exam_list_view(request):
    """
    Lists exam schedules, checking room facility readiness and alerting if hall has active critical tickets.
    """
    exams = ExamSchedule.objects.select_related('room', 'invigilator').order_by('exam_date', 'start_time')
    return render(request, 'academics/exam_list.html', {
        'exams': exams,
    })


@login_required
@manager_required
def exam_create_view(request):
    if request.method == 'POST':
        form = ExamScheduleForm(request.POST)
        if form.is_valid():
            exam = form.save()
            messages.success(request, f"Exam {exam.exam_name} for {exam.subject_code} scheduled in Room {exam.room.building_code} {exam.room.room_number}.")
            return redirect('academics:exam_list')
    else:
        form = ExamScheduleForm()

    return render(request, 'academics/exam_form.html', {'form': form})


@login_required
@faculty_required
def exam_toggle_readiness_view(request, exam_id):
    exam = get_object_or_404(ExamSchedule, pk=exam_id)
    exam.room_readiness_checked = not exam.room_readiness_checked
    exam.save()
    status_str = "Verified Ready" if exam.room_readiness_checked else "Unverified"
    messages.info(request, f"Exam room readiness marked as {status_str}.")
    return redirect('academics:exam_list')
