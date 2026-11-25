from django import forms
from .models import Announcement, FeeRecord
from accounts.models import User


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = [
            'title', 'announcement_type', 'target_role', 'target_department',
            'summary', 'body', 'event_date', 'due_date', 'is_pinned'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Annual Technical Symposium 2026'}),
            'announcement_type': forms.Select(attrs={'class': 'form-select'}),
            'target_role': forms.Select(attrs={'class': 'form-select'}),
            'target_department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional: e.g. Computer Science (Leave blank for all)'}),
            'summary': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief 1-sentence synopsis...'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Full details, schedule, venue, and instructions...'}),
            'event_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FeeRecordForm(forms.ModelForm):
    class Meta:
        model = FeeRecord
        fields = [
            'student', 'academic_term', 'fee_category', 'amount',
            'due_date', 'status', 'paid_date', 'receipt_number', 'remarks'
        ]
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'academic_term': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Fall 2026 - Semester 5'}),
            'fee_category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Tuition & Laboratory Fee'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'paid_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. REC-2026-9041'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(role=User.Role.STUDENT).order_by('identifier_number', 'username')

