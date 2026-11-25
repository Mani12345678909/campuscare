from datetime import timedelta
from django.utils import timezone
from accounts.models import AllowedEmailDomain
from notices.models import Announcement
from tickets.models import MaintenanceRequest
from academics.models import TimetableSlot


def recent_updates_processor(request):
    """
    Supplies real-time counts and spotlight data to base templates
    so navigation links and dashboard widgets highlight freshly updated data.
    """
    context = {
        'allowed_college_domains': [],
        'new_announcements_count': 0,
        'has_new_announcements': False,
        'new_tickets_count': 0,
        'has_new_tickets': False,
        'schedule_alerts_count': 0,
        'has_schedule_alerts': False,
        'spotlight_updates': [],
    }

    try:
        context['allowed_college_domains'] = AllowedEmailDomain.get_allowed_domain_list()
    except Exception:
        pass

    if not request.user.is_authenticated:
        return context

    now = timezone.now()
    since_24h = now - timedelta(hours=24)
    since_48h = now - timedelta(hours=48)

    user = request.user
    notices_cutoff = user.last_seen_notices_at or since_48h
    tickets_cutoff = user.last_seen_tickets_at or since_24h
    timetable_cutoff = user.last_seen_timetable_at

    try:
        # 1. New announcements (unseen since last visit)
        announcements_qs = Announcement.objects.filter(created_at__gt=notices_cutoff)
        if not (user.is_manager or user.is_admin_role):
            from django.db.models import Q
            role_q = Q(target_role=Announcement.TargetRole.ALL)
            if user.is_student:
                role_q |= Q(target_role=Announcement.TargetRole.STUDENT)
            elif user.is_faculty:
                role_q |= Q(target_role=Announcement.TargetRole.FACULTY)
            elif user.is_technician:
                role_q |= Q(target_role=Announcement.TargetRole.STAFF)
            announcements_qs = announcements_qs.filter(role_q)

        new_announcements_count = announcements_qs.count()
        context['new_announcements_count'] = new_announcements_count
        context['has_new_announcements'] = new_announcements_count > 0

        # 2. Tickets created or updated (unseen since last visit)
        tickets_qs = MaintenanceRequest.objects.filter(updated_at__gt=tickets_cutoff)
        if user.is_student:
            tickets_qs = tickets_qs.filter(reported_by=user)
        elif user.is_technician:
            from django.db.models import Q
            tickets_qs = tickets_qs.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))

        new_tickets_count = tickets_qs.count()
        context['new_tickets_count'] = new_tickets_count
        context['has_new_tickets'] = new_tickets_count > 0

        # 3. Schedule alerts (unseen since last visit)
        if timetable_cutoff:
            schedule_alerts_qs = TimetableSlot.objects.exclude(status='REGULAR').filter(updated_at__gt=timetable_cutoff)
        else:
            schedule_alerts_qs = TimetableSlot.objects.exclude(status='REGULAR')

        if user.is_student and user.department:
            schedule_alerts_qs = schedule_alerts_qs.filter(department=user.department)
        elif user.is_faculty:
            schedule_alerts_qs = schedule_alerts_qs.filter(faculty=user)

        schedule_alerts_count = schedule_alerts_qs.count()
        context['schedule_alerts_count'] = schedule_alerts_count
        context['has_schedule_alerts'] = schedule_alerts_count > 0

        # 4. Spotlight updates list
        spotlight = []
        for a in announcements_qs.order_by('-created_at')[:2]:
            spotlight.append({
                'type': 'ANNOUNCEMENT',
                'badge': 'NEW NOTICE',
                'badge_class': 'badge-rwb-notice',
                'icon': 'bi-megaphone-fill',
                'title': a.title,
                'summary': a.summary,
                'timestamp': a.created_at,
                'url': f"/notices/announcements/{a.id}/",
                'action_label': 'View Notice'
            })

        for t in tickets_qs.select_related('room').order_by('-updated_at')[:2]:
            spotlight.append({
                'type': 'TICKET',
                'badge': f'TICKET {t.get_status_display().upper()}',
                'badge_class': 'badge-rwb-ticket',
                'icon': 'bi-tools',
                'title': f"#{t.ticket_code}: {t.title}",
                'summary': f"Room {t.room.building_code} {t.room.room_number} &bull; Priority: {t.get_priority_display()}",
                'timestamp': t.updated_at,
                'url': f"/tickets/{t.ticket_code}/",
                'action_label': 'Inspect Ticket'
            })

        for s in schedule_alerts_qs.select_related('room')[:2]:
            spotlight.append({
                'type': 'SCHEDULE',
                'badge': f'SCHEDULE {s.get_status_display()}',
                'badge_class': 'badge-rwb-alert',
                'icon': 'bi-calendar-event',
                'title': f"{s.subject_code} {s.subject_name}",
                'summary': f"Room {s.room.building_code} {s.room.room_number} ({s.get_day_of_week_display()} P{s.period_number})",
                'timestamp': now,
                'url': "/academics/timetable/",
                'action_label': 'Check Timetable'
            })

        spotlight.sort(key=lambda x: x['timestamp'], reverse=True)
        context['spotlight_updates'] = spotlight[:4]

    except Exception:
        pass

    return context

