from django import forms
from django.utils import timezone
from .models import TimetableSlot, TeacherActivityLog, AttendanceSession, ExamSchedule
from facilities.models import Room
from accounts.models import User


class TimetableSlotForm(forms.ModelForm):
    class Meta:
        model = TimetableSlot
        fields = [
            'department', 'year', 'section', 'day_of_week', 'period_number',
            'start_time', 'end_time', 'subject_name', 'subject_code',
            'faculty', 'room', 'status', 'notes'
        ]
        widgets = {
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science & Engineering'}),
            'year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3rd Year'}),
            'section': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Section A'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'period_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'subject_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Advanced Operating Systems'}),
            'subject_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CS302'}),
            'faculty': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional instructions'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['faculty'].queryset = User.objects.filter(role__in=[User.Role.FACULTY, User.Role.ADMIN])
        self.fields['room'].queryset = Room.objects.filter(is_active=True).order_by('building_code', 'room_number')


class TeacherActivityLogForm(forms.ModelForm):
    class Meta:
        model = TeacherActivityLog
        fields = ['timetable_slot', 'date', 'room', 'session_status', 'topic_covered', 'remarks']
        widgets = {
            'timetable_slot': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'session_status': forms.Select(attrs={'class': 'form-select'}),
            'topic_covered': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detailed lecture topics or laboratory experiments executed...'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Student engagement, hardware problems, or equipment notes...'}),
        }

    def __init__(self, *args, faculty_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now().date()
        if faculty_user and not (faculty_user.is_manager or faculty_user.is_admin_role):
            self.fields['timetable_slot'].queryset = TimetableSlot.objects.filter(faculty=faculty_user)
        else:
            self.fields['timetable_slot'].queryset = TimetableSlot.objects.all()
        self.fields['room'].queryset = Room.objects.filter(is_active=True)


class ExamScheduleForm(forms.ModelForm):
    class Meta:
        model = ExamSchedule
        fields = [
            'exam_name', 'subject_name', 'subject_code', 'department',
            'year', 'section', 'exam_date', 'start_time', 'end_time',
            'room', 'invigilator', 'room_readiness_checked'
        ]
        widgets = {
            'exam_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Midterm Examination'}),
            'subject_name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject_code': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.TextInput(attrs={'class': 'form-control'}),
            'section': forms.TextInput(attrs={'class': 'form-control'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'invigilator': forms.Select(attrs={'class': 'form-select'}),
            'room_readiness_checked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].queryset = Room.objects.filter(is_active=True).order_by('building_code', 'room_number')
        self.fields['invigilator'].queryset = User.objects.filter(role__in=[User.Role.FACULTY, User.Role.MANAGER, User.Role.ADMIN])

