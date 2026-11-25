# CampusCare — Classroom Maintenance & Academic Operations System

A modular, production-structured **Classroom Maintenance & Academic Operations System** built with **Python**, **Django**, and **SQLite** (configured cleanly via `.env` so it can scale seamlessly to **PostgreSQL** in production).

---

## 1. Modular App Architecture

The system is organized into modular Django apps following separation-of-concerns principles:

```
class_room_management _system/
│
├── accounts/                  # Authentication, 2FA, onboarding & role permissions
│   ├── models.py              # User (roles: STUDENT, FACULTY, TECHNICIAN, MANAGER, ADMIN), OTPVerification
│   ├── middleware.py          # FirstLoginEnforcementMiddleware (enforces 2FA & onboarding)
│   ├── permissions.py         # Role decorators (@student_required, @faculty_required, etc.)
│   ├── forms.py               # Registration with college email domain validation, OTP, Onboarding
│   ├── views.py               # Auth, 2FA verification, OTP resend, onboarding, profile, role editing
│   └── urls.py
│
├── facilities/                # Campus buildings, rooms, and equipment assets
│   ├── models.py              # Room (operational status & unique constraint), Asset (equipment condition)
│   ├── forms.py               # Room & Asset forms
│   ├── views.py               # Room list, detail with assets & tickets, dynamic assets API
│   └── urls.py
│
├── tickets/                   # Maintenance tickets & problem reports
│   ├── models.py              # MaintenanceRequest (auto-generated code), TicketUpdate (audit log)
│   ├── forms.py               # Ticket submission (with report_type), status updates, triage/assign
│   ├── views.py               # Scoped listing, detail, status update, assign, live duplicate check API
│   └── urls.py
│
├── academics/                 # Timetables, teacher activity logs, attendance & exams
│   ├── models.py              # TimetableSlot, TeacherActivityLog, AttendanceSession, AttendanceRecord, ExamSchedule
│   ├── forms.py               # Timetable slot, activity log, and exam schedule forms
│   ├── views.py               # Weekly timetable grid, activity logs, student/staff attendance, exam readiness
│   └── urls.py
│
├── notices/                   # Campus notices, fee dues tracking, live feed & reports
│   ├── models.py              # Announcement (event/circulars), FeeRecord (due tracker)
│   ├── forms.py               # Announcement & FeeRecord creation forms
│   ├── views.py               # Circulars, fee tracker, live watch feed, reports hub, CSV exports
│   └── urls.py
│
├── core/                      # Main routing, role-aware dashboards & DB pragma setup
│   ├── views.py               # Role-aware dashboard (Student, Faculty, Technician, Manager)
│   ├── apps.py                # Enforces SQLite foreign keys (PRAGMA foreign_keys = ON)
│   └── management/commands/   # seed_data command for idempotent demo setup
│
├── templates/                 # Clean, responsive Bootstrap 5 templates
├── static/                    # Static files
├── media/                     # Uploaded ticket issue photos
├── .env.example               # Environment variables template
├── requirements.txt           # Dependencies
└── manage.py
```

---

## 2. Core Features by Module

### A. Authentication, Dynamic College Email Domains & First-Login 2FA (`accounts`)
- **Dynamic College Email Domain Administration**:
  - Signups are restricted to approved institutional domains.
  - **Admin Control Center (`/accounts/domains/`)**: System Administrators can view, add, toggle active/inactive, or remove authorized college email domains (e.g. `@mit.edu`, `@stanford.edu`, `@campus.ac.in`) directly from the web interface or Django Admin (`/admin/accounts/allowedemaildomain/`).
  - Active domains are loaded dynamically from the database and combined with `.env` fallbacks.
  - The registration form dynamically displays all currently authorized college domains for user convenience.
- **First-Login 2FA Verification**:
  - `is_first_login_2fa_completed` flag tracks verification status.
  - Generates a 6-digit cryptographic OTP (`OTPVerification` model with 10-minute expiry and attempt limits).
  - OTP is dispatched to the user's email (visible in the console in development).
  - `FirstLoginEnforcementMiddleware` prevents access to all operational dashboards until 2FA is verified.
- **One-Time Onboarding Profile Setup**:
  - After 2FA, redirects users to confirm department, Roll Number or Employee ID, Class Year/Section, and phone number before dashboard access.

### E. Real-Time Update Highlighting & Dashboard Spotlight (`core`)
- **Dynamic Navbar Highlighting**: Navigation links in the global header automatically display count badges and visual indicators (`New`, `Alerts`, `Live`) when fresh notices, updated maintenance tickets, or rescheduled classes occur.
- **"What's New" Spotlight Widget**: The main operations dashboard features a prominent spotlight banner highlighting newly added and updated institutional data across all modules with direct one-click navigation buttons (`View Notice &rarr;`, `Inspect Ticket &rarr;`, `Check Timetable &rarr;`).

### F. Classroom Maintenance & Equipment Asset Tracking (`facilities` & `tickets`)
- **Classroom Live Status**: `Room` tracks status (`AVAILABLE`, `OCCUPIED`, `MAINTENANCE`, `RESERVED`) with unique constraint on `(building_code, room_number)`.
- **Equipment Assets**: `Asset` tracks AV/IT, HVAC, electrical, and plumbing equipment (`OPERATIONAL`, `NEEDS_REPAIR`, `OUT_OF_SERVICE`).
- **Maintenance Tickets**:
  - Auto-generated ticket code (e.g. `CM-2026-0001`).
  - Report types: `MAINTENANCE`, `FACILITY_ISSUE`, `ACADEMIC_OPERATIONAL`.
  - Dynamic room asset filtering via `/facilities/api/rooms/<id>/assets/`.
  - Live duplicate warning banner via `/tickets/api/check-duplicates/` alerts users of active room issues before submission.
  - Complete `TicketUpdate` audit timeline with author, status transition, timestamp, and work comments.

### C. Timetables, Attendance, Teacher Activity & Exams (`academics`)
- **Weekly Timetable (`TimetableSlot`)**: Period scheduling filtered by section, faculty, or classroom venue. Supports statuses: `REGULAR`, `SUBSTITUTED`, `RESCHEDULED`, `CANCELLED`.
- **Teacher Class Activity Logs (`TeacherActivityLog`)**: Faculty log daily conducted lectures, syllabus topics covered, and classroom equipment observations.
- **Attendance System (`AttendanceSession` & `AttendanceRecord`)**:
  - Faculty mark `PRESENT`, `ABSENT`, `LATE`, or `ON_DUTY` per student.
  - Unique constraint on `(timetable_slot, date)` strictly prevents duplicate sessions.
  - Subject-wise and aggregate attendance percentage calculations for students.
  - Low-attendance alerts (`<75%` threshold) highlighted on student and faculty dashboards.
- **Exam Scheduling & Room Readiness (`ExamSchedule`)**:
  - Exam dates, sessions, halls, and invigilator assignments.
  - Automated room readiness check: Flags exam halls that have active critical/high maintenance requests so issues are rectified before exams.

### D. Campus Notices, Fee Due Tracker, Live Watch Feed & CSV Reports (`notices`)
- **Announcements & Events (`Announcement`)**: Official campus notices (`GENERAL`, `EVENT`, `FEE_NOTICE`, `EXAM_UPDATE`, `MAINTENANCE_ALERT`) targeted by role and department with pinning.
- **Student Fee Due Tracker (`FeeRecord`)**: Student visibility into tuition and lab dues, deadlines, payment receipts, and scholarship waivers.
- **Unified Live Watch Feed (`/notices/feed/`)**: Real-time chronological activity stream aggregating maintenance tickets, room status changes, timetable substitutions, upcoming exams, fee deadlines, and announcements with category filters.
- **One-Click CSV Export Reports (`/notices/reports/`)**:
  1. **Maintenance & Recurring Room Faults Report**: `/notices/reports/maintenance/csv/`
  2. **Student Attendance Summary Report**: `/notices/reports/attendance/csv/`
  3. **Teacher Activity & Class Log Report**: `/notices/reports/teacher-activity/csv/`

---

## 3. Demo Login Accounts

Run `python manage.py seed_data` to populate or reset realistic demo data:

| Role | Username | Password | Purpose & Notes |
| :--- | :--- | :--- | :--- |
| **ADMIN** | `admin` | `AdminPass123!` | Superuser & Campus Admin (2FA verified) |
| **MANAGER** | `manager` | `ManagerPass123!` | Facilities Ops Manager; KPI dashboards, triage & fee tracking (2FA verified) |
| **FACULTY** | `prof_john` | `FacultyPass123!` | Professor (CS); teaching schedule, attendance, class logs (2FA verified) |
| **FACULTY** | `prof_emily` | `FacultyPass123!` | Professor (CS); lab incharge & exam invigilator (2FA verified) |
| **TECHNICIAN** | `tech_sarah` | `TechPass123!` | AV & IT technical specialist; repair queue (2FA verified) |
| **TECHNICIAN** | `tech_mike` | `TechPass123!` | HVAC & mechanical systems specialist (2FA verified) |
| **STUDENT** | `student_alex` | `StudentPass123!` | Roll: `21CS001`; 100% attendance, cleared fee records (2FA verified) |
| **STUDENT** | `student_priya` | `StudentPass123!` | Roll: `21CS042`; **<75% Low Attendance Alert**, overdue fee notice (2FA verified) |
| **STUDENT** | `new_student` | `StudentPass123!` | **Pending 2FA & Onboarding** (test live OTP entry & onboarding setup!) |

---

## 4. Setup & Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env file
cp .env.example .env

# 3. Apply database migrations
python manage.py migrate

# 4. Populate realistic demo data (idempotent)
python manage.py seed_data

# 5. Run automated test suite
python manage.py test

# 6. Start development server
python manage.py runserver 127.0.0.1:8000
```

Open your browser to: **http://127.0.0.1:8000/**

---

## 5. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DEBUG` | `True` | Set to `False` in production |
| `SECRET_KEY` | *(django-insecure dev key)* | Cryptographic signing secret |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Hostnames permitted to serve traffic |
| `DATABASE_URL` | `sqlite:///db.sqlite3` | SQLite default; set to PostgreSQL URL for production |
| `ALLOWED_EMAIL_DOMAINS` | `college.edu,university.edu` | Approved email domains for user registration |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Console backend for OTPs in dev; SMTP in production |

---

## 6. Migrating from SQLite to PostgreSQL

1. Install psycopg2:
   ```bash
   pip install psycopg2-binary
   ```
2. In `.env`, change `DATABASE_URL`:
   ```env
   DATABASE_URL=postgres://postgres_user:your_password@localhost:5432/classroom_academic_db
   ```
3. Run migrations and seed data on PostgreSQL:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   ```

---

## 7. Automated Test Suite

Run all 27 automated unit and integration tests across apps:
```bash
python manage.py test
```
Covers:
- College email domain validation (allowed vs unauthorized domains)
- First-login 2FA OTP verification and onboarding redirect
- Middleware blocking unverified users from dashboards
- Maintenance ticket submission, code auto-generation, and status update audit logs
- Dynamic duplicate ticket check API
- Attendance session duplicate prevention on same slot + date
- Subject-wise and aggregate attendance percentage calculations (<75% threshold)
- Teacher activity logging
- Exam hall readiness check (flagging active critical maintenance)
- Announcement role filtering and fee dues balance calculations
- All 3 CSV export endpoints (Maintenance, Attendance, Activity Logs)
- SQLite foreign key pragma enforcement check
