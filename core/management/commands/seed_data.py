from datetime import date, time, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, OTPVerification
from facilities.models import Room, Asset
from tickets.models import MaintenanceRequest, TicketUpdate
from academics.models import TimetableSlot, TeacherActivityLog, AttendanceSession, AttendanceRecord, ExamSchedule
from notices.models import Announcement, FeeRecord


class Command(BaseCommand):
    help = "Idempotently populates realistic sample data across all academic, facility, and maintenance modules."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("==> Seeding CampusCare Academic & Facilities System..."))

        # 1. Seed Users (using @college.edu domains)
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@college.edu',
                'password': 'AdminPass123!',
                'first_name': 'Eleanor',
                'last_name': 'Vance',
                'role': User.Role.ADMIN,
                'department': 'Campus Operations & IT',
                'identifier_number': 'EMP-ADM-01',
                'year_or_block': 'Admin Tower / Suite 400',
                'is_staff': True,
                'is_superuser': True,
                'is_first_login_2fa_completed': True,
                'is_onboarding_completed': True,
            },
            {
                'username': 'manager',
                'email': 'manager@college.edu',
                'password': 'ManagerPass123!',
                'first_name': 'Marcus',
                'last_name': 'Sterling',
                'role': User.Role.MANAGER,
                'department': 'Facilities Management Directorate',
                'identifier_number': 'EMP-MGR-02',
                'year_or_block': 'Central Facilities Office',
                'is_staff': True,
                'is_superuser': False,
                'is_first_login_2fa_completed': True,
                'is_onboarding_completed': True,
            },
            {
                'username': 'tech_sarah',
                'email': 'tech_sarah@college.edu',
                'password': 'TechPass123!',
                'first_name': 'Sarah',
                'last_name': 'Chen',
                'role': User.Role.TECHNICIAN,
                'department': 'AV & Digital Infrastructure',
                'identifier_number': 'EMP-TECH-10',
                'year_or_block': 'Technical Workshop B',
                'is_staff': False,
                'is_superuser': False,
                'is_first_login_2fa_completed': True,
                'is_onboarding_completed': True,
            },
            {
                'username': 'tech_mike',
                'email': 'tech_mike@college.edu',
                'password': 'TechPass123!',
                'first_name': 'Michael',
                'last_name': 'O’Connor',
                'role': User.Role.TECHNICIAN,
                'department': 'HVAC & Mechanical Systems',
                'identifier_number': 'EMP-TECH-11',
                'year_or_block': 'Physical Plant Basement',
                'is_staff': False,
                'is_superuser': False,
                'is_first_login_2fa_completed': True,
                'is_onboarding_completed': True,
            },
            {
                'username': 'prof_john',
                'email': 'prof_john@college.edu',
                'password': 'FacultyPass123!',
                'first_name': 'Dr. John',
                'last_name': 'Doe',
                'role': User.Role.FACULTY,
                'department': 'Computer Science & Engineering',
                'identifier_number': 'EMP-FAC-101',
                'year_or_block': 'Turing Hall / Office 302',
                'is_staff': False,
                'is_superuser': False,
                'is_first_login_2fa_completed': True,
                'is_onboarding_completed': True,
            },
            {
                'username': 'prof_emily',
                'email': 'prof_emily@college.edu',
                'password': 'FacultyPass123!',
                'first_name': 'Dr. Emily',
                'last_name': 'Watson',
                'role': User.Role.FACULTY,
                'department': 'Computer Science & Engineering',
                'identifier_number': 'EMP-FAC-102',
                'year_or_block': 'Turing Hall / Office 305',
                'is_staff': False,
                'is_superuser': False,
                'is_first_login_2fa_completed': True,
                'is_onboarding_completed': True,
            },
            {
                'username': 'student_alex',
                'email': 'student_alex@college.edu',
                'password': 'StudentPass123!',
                'first_name': 'Alex',
                'last_name': 'Rivera',
                'role': User.Role.STUDENT,
                'department': 'Computer Science & Engineering',
                'identifier_number': '21CS001',
                'year_or_block': '3rd Year / Section A',
                'is_staff': False,
                'is_superuser': False,
                'is_first_login_2fa_completed': True,
                'is_onboarding_completed': True,
            },
            {
                'username': 'student_priya',
                'email': 'student_priya@college.edu',
                'password': 'StudentPass123!',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'role': User.Role.STUDENT,
                'department': 'Computer Science & Engineering',
                'identifier_number': '21CS042',
                'year_or_block': '3rd Year / Section A',
                'is_staff': False,
                'is_superuser': False,
                'is_first_login_2fa_completed': True,
                'is_onboarding_completed': True,
            },
            # Demo User for testing 2FA OTP & Onboarding
            {
                'username': 'new_student',
                'email': 'new_student@college.edu',
                'password': 'StudentPass123!',
                'first_name': 'Jordan',
                'last_name': 'Lee',
                'role': User.Role.STUDENT,
                'department': 'Computer Science & Engineering',
                'identifier_number': '21CS099',
                'year_or_block': '3rd Year / Section A',
                'is_staff': False,
                'is_superuser': False,
                'is_first_login_2fa_completed': False,
                'is_onboarding_completed': False,
            },
        ]

        created_users = {}
        for udata in users_data:
            user, created = User.objects.get_or_create(username=udata['username'])
            for key, val in udata.items():
                if key == 'password':
                    user.set_password(val)
                else:
                    setattr(user, key, val)
            user.save()
            created_users[udata['username']] = user
            status_str = "Created" if created else "Updated"
            self.stdout.write(f"  [{status_str}] User: {user.username} ({user.get_role_display()})")

        # 1.5 Seed Authorized College Email Domains
        from accounts.models import AllowedEmailDomain
        domains_data = [
            {'domain': 'college.edu', 'college_name': 'Imperial College of Technology', 'is_active': True},
            {'domain': 'university.edu', 'college_name': 'State Central University', 'is_active': True},
            {'domain': 'stanford.edu', 'college_name': 'Stanford University', 'is_active': True},
            {'domain': 'mit.edu', 'college_name': 'Massachusetts Institute of Technology', 'is_active': True},
        ]
        for ddata in domains_data:
            dom, created = AllowedEmailDomain.objects.get_or_create(
                domain=ddata['domain'],
                defaults={
                    'college_name': ddata['college_name'],
                    'is_active': ddata['is_active'],
                    'created_by': created_users.get('admin')
                }
            )
            d_status = "Created" if created else "Retained"
            self.stdout.write(f"  [{d_status}] Allowed Domain: @{dom.domain} ({dom.college_name})")

        # 2. Seed Rooms
        rooms_data = [
            {
                'building_name': 'Science & Engineering Complex',
                'building_code': 'SEC',
                'floor': '1st Floor',
                'room_number': '101',
                'room_type': Room.RoomType.LECTURE_HALL,
                'capacity': 120,
                'operational_status': Room.OperationalStatus.AVAILABLE,
            },
            {
                'building_name': 'Science & Engineering Complex',
                'building_code': 'SEC',
                'floor': '1st Floor',
                'room_number': '102',
                'room_type': Room.RoomType.LAB,
                'capacity': 36,
                'operational_status': Room.OperationalStatus.OCCUPIED,
            },
            {
                'building_name': 'Science & Engineering Complex',
                'building_code': 'SEC',
                'floor': '2nd Floor',
                'room_number': '205',
                'room_type': Room.RoomType.SEMINAR_HALL,
                'capacity': 24,
                'operational_status': Room.OperationalStatus.AVAILABLE,
            },
            {
                'building_name': 'Alan Turing Academic Hall',
                'building_code': 'TAH',
                'floor': '3rd Floor',
                'room_number': '301',
                'room_type': Room.RoomType.CLASSROOM,
                'capacity': 48,
                'operational_status': Room.OperationalStatus.AVAILABLE,
            },
            {
                'building_name': 'Alan Turing Academic Hall',
                'building_code': 'TAH',
                'floor': '3rd Floor',
                'room_number': '304',
                'room_type': Room.RoomType.LAB,
                'capacity': 40,
                'operational_status': Room.OperationalStatus.OCCUPIED,
            },
            {
                'building_name': 'Alan Turing Academic Hall',
                'building_code': 'TAH',
                'floor': '4th Floor',
                'room_number': '410',
                'room_type': Room.RoomType.LECTURE_HALL,
                'capacity': 180,
                'operational_status': Room.OperationalStatus.RESERVED,
            },
            {
                'building_name': 'Isaac Newton Research Wing',
                'building_code': 'NWT',
                'floor': '1st Floor',
                'room_number': '101',
                'room_type': Room.RoomType.CLASSROOM,
                'capacity': 50,
                'operational_status': Room.OperationalStatus.AVAILABLE,
            },
            {
                'building_name': 'Isaac Newton Research Wing',
                'building_code': 'NWT',
                'floor': '2nd Floor',
                'room_number': '202',
                'room_type': Room.RoomType.LAB,
                'capacity': 30,
                'operational_status': Room.OperationalStatus.MAINTENANCE,
            },
        ]

        created_rooms = {}
        for rdata in rooms_data:
            room, created = Room.objects.get_or_create(
                building_code=rdata['building_code'],
                room_number=rdata['room_number'],
                defaults=rdata
            )
            if not created:
                for key, val in rdata.items():
                    setattr(room, key, val)
                room.save()
            created_rooms[f"{room.building_code}-{room.room_number}"] = room

        # 3. Seed Assets
        assets_data = [
            {'room_key': 'SEC-101', 'name': 'Overhead 4K Laser Projector', 'asset_tag': 'AST-SEC101-01', 'category': Asset.Category.AV_IT, 'status': Asset.Condition.OPERATIONAL},
            {'room_key': 'SEC-101', 'name': 'Daikin Central Inverter AC 5-Ton', 'asset_tag': 'AST-SEC101-02', 'category': Asset.Category.HVAC, 'status': Asset.Condition.NEEDS_REPAIR},
            {'room_key': 'SEC-102', 'name': 'Interactive Touch SmartBoard 86"', 'asset_tag': 'AST-SEC102-01', 'category': Asset.Category.AV_IT, 'status': Asset.Condition.OPERATIONAL},
            {'room_key': 'TAH-301', 'name': 'Ceiling Luminaire LED Panel Grid', 'asset_tag': 'AST-TAH301-01', 'category': Asset.Category.ELECTRICAL, 'status': Asset.Condition.OPERATIONAL},
            {'room_key': 'TAH-304', 'name': 'Dell Precision Rack Workstation Node', 'asset_tag': 'AST-TAH304-01', 'category': Asset.Category.AV_IT, 'status': Asset.Condition.NEEDS_REPAIR},
            {'room_key': 'NWT-202', 'name': 'Chemical Fume Hood Exhaust System', 'asset_tag': 'AST-NWT202-01', 'category': Asset.Category.HVAC, 'status': Asset.Condition.OUT_OF_SERVICE},
            {'room_key': 'NWT-202', 'name': 'Laboratory Stainless Wash Sink', 'asset_tag': 'AST-NWT202-02', 'category': Asset.Category.PLUMBING, 'status': Asset.Condition.NEEDS_REPAIR},
        ]

        created_assets = {}
        for adata in assets_data:
            room = created_rooms[adata['room_key']]
            asset, created = Asset.objects.get_or_create(
                asset_tag=adata['asset_tag'],
                defaults={
                    'room': room,
                    'name': adata['name'],
                    'category': adata['category'],
                    'status': adata['status'],
                    'installed_on': date(2023, 6, 15),
                }
            )
            created_assets[adata['asset_tag']] = asset

        # 4. Seed Maintenance Tickets
        tickets_data = [
            {
                'title': 'Projector display flickers and shows pink hue',
                'room_key': 'SEC-101',
                'asset_tag': 'AST-SEC101-01',
                'reported_by': created_users['prof_john'],
                'assigned_to': None,
                'report_type': MaintenanceRequest.ReportType.MAINTENANCE,
                'category': MaintenanceRequest.Category.AV_IT,
                'priority': MaintenanceRequest.Priority.HIGH,
                'status': MaintenanceRequest.Status.SUBMITTED,
                'description': 'During CS301 lectures, the overhead projector keeps flickering and the HDMI color is distorted.',
                'resolution_notes': '',
            },
            {
                'title': 'AC unit dripping water onto student seating area',
                'room_key': 'SEC-101',
                'asset_tag': 'AST-SEC101-02',
                'reported_by': created_users['student_alex'],
                'assigned_to': created_users['tech_mike'],
                'report_type': MaintenanceRequest.ReportType.MAINTENANCE,
                'category': MaintenanceRequest.Category.HVAC,
                'priority': MaintenanceRequest.Priority.CRITICAL,
                'status': MaintenanceRequest.Status.ASSIGNED,
                'description': 'Condensation tray is overflowing and dripping onto rows 2 and 3. Risk of slipping hazard.',
                'resolution_notes': '',
            },
            {
                'title': 'Fume hood ventilation blower motor bearing failure',
                'room_key': 'NWT-202',
                'asset_tag': 'AST-NWT202-01',
                'reported_by': created_users['prof_john'],
                'assigned_to': created_users['tech_mike'],
                'report_type': MaintenanceRequest.ReportType.MAINTENANCE,
                'category': MaintenanceRequest.Category.HVAC,
                'priority': MaintenanceRequest.Priority.CRITICAL,
                'status': MaintenanceRequest.Status.NEEDS_PARTS,
                'description': 'Loud grinding sound and safety airflow sensor tripped. Blower motor bearing is seized.',
                'resolution_notes': '',
            },
            {
                'title': 'Workstation cluster network switch packet loss',
                'room_key': 'TAH-304',
                'asset_tag': 'AST-TAH304-01',
                'reported_by': created_users['prof_emily'],
                'assigned_to': created_users['tech_sarah'],
                'report_type': MaintenanceRequest.ReportType.ACADEMIC_OPERATIONAL,
                'category': MaintenanceRequest.Category.AV_IT,
                'priority': MaintenanceRequest.Priority.HIGH,
                'status': MaintenanceRequest.Status.IN_PROGRESS,
                'description': 'Lab computers in row B are unable to reach the departmental server consistently.',
                'resolution_notes': '',
            },
            {
                'title': 'SmartBoard touch calibration offset and HDMI replacement',
                'room_key': 'SEC-102',
                'asset_tag': 'AST-SEC102-01',
                'reported_by': created_users['prof_emily'],
                'assigned_to': created_users['tech_sarah'],
                'report_type': MaintenanceRequest.ReportType.MAINTENANCE,
                'category': MaintenanceRequest.Category.AV_IT,
                'priority': MaintenanceRequest.Priority.MEDIUM,
                'status': MaintenanceRequest.Status.RESOLVED,
                'description': 'Stylus touches were registering offset from contact point.',
                'resolution_notes': 'Replaced wall plate with new 4K 60Hz HDMI keystone and recalibrated optical touch matrix.',
            },
        ]

        for tdata in tickets_data:
            room = created_rooms[tdata['room_key']]
            asset = created_assets.get(tdata['asset_tag'])
            ticket, created = MaintenanceRequest.objects.get_or_create(
                title=tdata['title'],
                room=room,
                defaults={
                    'asset': asset,
                    'reported_by': tdata['reported_by'],
                    'assigned_to': tdata['assigned_to'],
                    'report_type': tdata['report_type'],
                    'category': tdata['category'],
                    'priority': tdata['priority'],
                    'status': tdata['status'],
                    'description': tdata['description'],
                    'resolution_notes': tdata['resolution_notes'],
                }
            )
            if created or ticket.updates.count() == 0:
                TicketUpdate.objects.create(
                    ticket=ticket,
                    author=tdata['reported_by'],
                    new_status=MaintenanceRequest.Status.SUBMITTED,
                    comment="Initial issue report logged."
                )
                if tdata['status'] in [MaintenanceRequest.Status.ASSIGNED, MaintenanceRequest.Status.IN_PROGRESS]:
                    TicketUpdate.objects.create(
                        ticket=ticket,
                        author=created_users['manager'],
                        old_status=MaintenanceRequest.Status.SUBMITTED,
                        new_status=tdata['status'],
                        comment="Triage complete; technician dispatched."
                    )
                elif tdata['status'] == MaintenanceRequest.Status.RESOLVED:
                    TicketUpdate.objects.create(
                        ticket=ticket,
                        author=created_users['tech_sarah'],
                        old_status=MaintenanceRequest.Status.IN_PROGRESS,
                        new_status=MaintenanceRequest.Status.RESOLVED,
                        comment=f"Repairs completed: {tdata['resolution_notes']}"
                    )

        # 5. Seed Timetable Slots
        slots_data = [
            {
                'department': 'Computer Science & Engineering', 'year': '3rd Year', 'section': 'Section A',
                'day_of_week': 'MON', 'period_number': 1, 'start_time': time(9, 0), 'end_time': time(9, 50),
                'subject_name': 'Database Management Systems', 'subject_code': 'CS301',
                'faculty': created_users['prof_john'], 'room': created_rooms['SEC-101'], 'status': TimetableSlot.SlotStatus.REGULAR
            },
            {
                'department': 'Computer Science & Engineering', 'year': '3rd Year', 'section': 'Section A',
                'day_of_week': 'MON', 'period_number': 2, 'start_time': time(10, 0), 'end_time': time(10, 50),
                'subject_name': 'Computer Networks', 'subject_code': 'CS302',
                'faculty': created_users['prof_emily'], 'room': created_rooms['TAH-301'], 'status': TimetableSlot.SlotStatus.REGULAR
            },
            {
                'department': 'Computer Science & Engineering', 'year': '3rd Year', 'section': 'Section A',
                'day_of_week': 'TUE', 'period_number': 1, 'start_time': time(9, 0), 'end_time': time(9, 50),
                'subject_name': 'Design and Analysis of Algorithms', 'subject_code': 'CS303',
                'faculty': created_users['prof_john'], 'room': created_rooms['TAH-301'], 'status': TimetableSlot.SlotStatus.REGULAR
            },
            {
                'department': 'Computer Science & Engineering', 'year': '3rd Year', 'section': 'Section A',
                'day_of_week': 'TUE', 'period_number': 3, 'start_time': time(11, 0), 'end_time': time(12, 40),
                'subject_name': 'Networks & Operating Systems Lab', 'subject_code': 'CS304L',
                'faculty': created_users['prof_emily'], 'room': created_rooms['TAH-304'], 'status': TimetableSlot.SlotStatus.REGULAR
            },
            {
                'department': 'Computer Science & Engineering', 'year': '3rd Year', 'section': 'Section A',
                'day_of_week': 'WED', 'period_number': 2, 'start_time': time(10, 0), 'end_time': time(10, 50),
                'subject_name': 'Software Engineering', 'subject_code': 'CS305',
                'faculty': created_users['prof_emily'], 'room': created_rooms['SEC-101'], 'status': TimetableSlot.SlotStatus.SUBSTITUTED,
                'notes': 'Dr. Watson substituting for Dr. John Doe'
            },
        ]

        created_slots = []
        for sdata in slots_data:
            slot, created = TimetableSlot.objects.get_or_create(
                department=sdata['department'],
                section=sdata['section'],
                day_of_week=sdata['day_of_week'],
                period_number=sdata['period_number'],
                defaults=sdata
            )
            created_slots.append(slot)

        # 6. Seed Teacher Activity Logs
        today = timezone.now().date()
        logs_data = [
            {
                'slot': created_slots[0],
                'date': today - timedelta(days=2),
                'faculty': created_users['prof_john'],
                'room': created_rooms['SEC-101'],
                'topic': 'ER-Modeling, Normalization up to BCNF, Relational Schema Mapping',
                'status': TeacherActivityLog.SessionStatus.CONDUCTED,
                'remarks': 'Projector had slight hue offset; maintenance ticket filed.',
            },
            {
                'slot': created_slots[1],
                'date': today - timedelta(days=2),
                'faculty': created_users['prof_emily'],
                'room': created_rooms['TAH-301'],
                'topic': 'Transport Layer: TCP 3-Way Handshake, Flow & Congestion Control',
                'status': TeacherActivityLog.SessionStatus.CONDUCTED,
                'remarks': 'Excellent class engagement; Wireshark packet capture demonstrated live.',
            },
            {
                'slot': created_slots[3],
                'date': today - timedelta(days=1),
                'faculty': created_users['prof_emily'],
                'room': created_rooms['TAH-304'],
                'topic': 'Socket Programming in C: Multithreaded TCP Echo Server & Client',
                'status': TeacherActivityLog.SessionStatus.LAB_HELD,
                'remarks': 'Node B switch had packet loss; technician Sarah notified.',
            },
        ]

        for ldata in logs_data:
            TeacherActivityLog.objects.get_or_create(
                timetable_slot=ldata['slot'],
                date=ldata['date'],
                defaults={
                    'faculty': ldata['faculty'],
                    'room': ldata['room'],
                    'topic_covered': ldata['topic'],
                    'session_status': ldata['status'],
                    'remarks': ldata['remarks'],
                }
            )

        # 7. Seed Attendance Sessions & Records (Priya has lower attendance <75% for test verification)
        students_cohort = [created_users['student_alex'], created_users['student_priya']]

        att_dates = [today - timedelta(days=5), today - timedelta(days=3), today - timedelta(days=2), today - timedelta(days=1)]
        slot_for_att = created_slots[0]  # CS301

        for idx, att_date in enumerate(att_dates):
            session, created = AttendanceSession.objects.get_or_create(
                timetable_slot=slot_for_att,
                date=att_date,
                defaults={'conducted_by': created_users['prof_john']}
            )
            # Alex is always PRESENT (100%)
            AttendanceRecord.objects.get_or_create(
                session=session,
                student=created_users['student_alex'],
                defaults={'status': AttendanceRecord.Status.PRESENT}
            )
            # Priya was present only in the first session (1 out of 4 = 25% < 75%)
            priya_status = AttendanceRecord.Status.PRESENT if idx == 0 else AttendanceRecord.Status.ABSENT
            AttendanceRecord.objects.get_or_create(
                session=session,
                student=created_users['student_priya'],
                defaults={'status': priya_status, 'remarks': 'Medical absence' if idx == 1 else ''}
            )

        # 8. Seed Exam Schedules
        exams_data = [
            {
                'exam_name': 'Midterm Theory Examination',
                'subject_name': 'Database Management Systems',
                'subject_code': 'CS301',
                'department': 'Computer Science & Engineering',
                'year': '3rd Year',
                'section': 'Section A',
                'exam_date': today + timedelta(days=7),
                'start_time': time(10, 0),
                'end_time': time(12, 0),
                'room': created_rooms['SEC-101'],
                'invigilator': created_users['prof_emily'],
                'room_readiness_checked': False,
            },
            {
                'exam_name': 'Laboratory Practical Evaluation',
                'subject_name': 'Networks & Operating Systems Lab',
                'subject_code': 'CS304L',
                'department': 'Computer Science & Engineering',
                'year': '3rd Year',
                'section': 'Section A',
                'exam_date': today + timedelta(days=10),
                'start_time': time(14, 0),
                'end_time': time(17, 0),
                'room': created_rooms['TAH-304'],
                'invigilator': created_users['prof_john'],
                'room_readiness_checked': True,
            },
            {
                'exam_name': 'End Semester Written Exam',
                'subject_name': 'Organic Chemistry & Synthesis',
                'subject_code': 'CH202',
                'department': 'Chemical Sciences',
                'year': '2nd Year',
                'section': 'Section B',
                'exam_date': today + timedelta(days=14),
                'start_time': time(9, 30),
                'end_time': time(12, 30),
                'room': created_rooms['NWT-202'],  # Has critical maintenance issue!
                'invigilator': created_users['prof_john'],
                'room_readiness_checked': False,
            },
        ]

        for edata in exams_data:
            ExamSchedule.objects.get_or_create(
                exam_name=edata['exam_name'],
                subject_code=edata['subject_code'],
                exam_date=edata['exam_date'],
                defaults=edata
            )

        # 9. Seed Announcements
        announcements_data = [
            {
                'title': 'Midterm Examination Schedule Released',
                'summary': 'The Fall 2026 Midterm schedule is published for all 3rd Year B.Tech programs.',
                'body': 'Please review allocated examination halls and reporting times. Calculators are permitted only for numerical courses.',
                'announcement_type': Announcement.Type.EXAM_UPDATE,
                'target_role': Announcement.TargetRole.STUDENT,
                'due_date': today + timedelta(days=7),
                'is_pinned': True,
                'created_by': created_users['admin'],
            },
            {
                'title': 'Campus Annual Technical Hackathon 2026',
                'summary': '48-hour inter-college software and IoT hackathon in the Turing Innovation Hall.',
                'body': 'Open to all undergraduate students. Registrations close on Friday. Prizes include lab sponsorship and tech vouchers.',
                'announcement_type': Announcement.Type.EVENT,
                'target_role': Announcement.TargetRole.ALL,
                'event_date': today + timedelta(days=18),
                'is_pinned': True,
                'created_by': created_users['manager'],
            },
            {
                'title': 'Semester Laboratory Fee Due Notice',
                'summary': 'Final deadline for payment of Semester 5 Advanced Computing lab fees.',
                'body': 'Students must settle lab consumables fee before practical examination cards are generated by the registrar.',
                'announcement_type': Announcement.Type.FEE_NOTICE,
                'target_role': Announcement.TargetRole.STUDENT,
                'due_date': today + timedelta(days=12),
                'is_pinned': False,
                'created_by': created_users['manager'],
            },
            {
                'title': 'Physical Plant Scheduled HVAC Filter Maintenance',
                'summary': 'Air conditioning servicing in Science & Engineering Complex wings on Saturday.',
                'body': 'Technical teams will be replacing high-efficiency HEPA filters across all SEC 1st floor classrooms between 8:00 AM and 2:00 PM.',
                'announcement_type': Announcement.Type.MAINTENANCE_ALERT,
                'target_role': Announcement.TargetRole.ALL,
                'event_date': today + timedelta(days=3),
                'is_pinned': False,
                'created_by': created_users['tech_mike'],
            },
        ]

        for adata in announcements_data:
            Announcement.objects.get_or_create(
                title=adata['title'],
                defaults=adata
            )

        # 10. Seed Student Fee Records
        fees_data = [
            {
                'student': created_users['student_alex'],
                'academic_term': 'Fall 2026 - Semester 5',
                'fee_category': 'Tuition & Infrastructure Fee',
                'amount': Decimal('3250.00'),
                'due_date': today - timedelta(days=15),
                'status': FeeRecord.Status.PAID,
                'paid_date': today - timedelta(days=20),
                'receipt_number': 'REC-2026-CS001',
            },
            {
                'student': created_users['student_alex'],
                'academic_term': 'Fall 2026 - Semester 5',
                'fee_category': 'Computing & Lab Consumables',
                'amount': Decimal('450.00'),
                'due_date': today + timedelta(days=12),
                'status': FeeRecord.Status.PENDING,
            },
            {
                'student': created_users['student_priya'],
                'academic_term': 'Fall 2026 - Semester 5',
                'fee_category': 'Tuition & Infrastructure Fee',
                'amount': Decimal('3250.00'),
                'due_date': today - timedelta(days=5),
                'status': FeeRecord.Status.OVERDUE,
            },
        ]

        for fdata in fees_data:
            FeeRecord.objects.get_or_create(
                student=fdata['student'],
                academic_term=fdata['academic_term'],
                fee_category=fdata['fee_category'],
                defaults=fdata
            )

        self.stdout.write(self.style.SUCCESS("\n==> Successfully seeded CampusCare System with realistic academic & facilities data!"))
        self.stdout.write(self.style.NOTICE("""
Available Demo Accounts (@college.edu):
--------------------------------------------------------------------------------------
Role         | Username      | Password        | Description / 2FA Status
--------------------------------------------------------------------------------------
ADMIN        | admin         | AdminPass123!   | Superuser & Campus Admin (2FA verified)
MANAGER      | manager       | ManagerPass123! | Facilities Operations Manager (2FA verified)
FACULTY      | prof_john     | FacultyPass123! | Faculty (CS) & Timetable Instructor (2FA verified)
FACULTY      | prof_emily    | FacultyPass123! | Faculty (CS) & Lab Incharge (2FA verified)
TECHNICIAN   | tech_sarah    | TechPass123!    | AV & IT Technical Specialist (2FA verified)
TECHNICIAN   | tech_mike     | TechPass123!    | HVAC & Plumbing Specialist (2FA verified)
STUDENT      | student_alex  | StudentPass123! | Roll: 21CS001 (100% Attendance, Fees Cleared)
STUDENT      | student_priya | StudentPass123! | Roll: 21CS042 (25% Low Attendance Alert, Overdue Fee)
STUDENT      | new_student   | StudentPass123! | First-Login 2FA & Onboarding Pending (Demo OTP tester)
--------------------------------------------------------------------------------------
"""))
