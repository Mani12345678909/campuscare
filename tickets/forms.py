from django import forms
from .models import MaintenanceRequest, TicketUpdate
from facilities.models import Room, Asset
from accounts.models import User


class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ['report_type', 'room', 'asset', 'category', 'priority', 'title', 'description', 'issue_photo']
        widgets = {
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select', 'id': 'id_room'}),
            'asset': forms.Select(attrs={'class': 'form-select', 'id': 'id_asset'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Projector HDMI port broken / AC blowing warm air'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Please provide specific details about the issue, symptoms, and urgency...'}),
            'issue_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].queryset = Room.objects.filter(is_active=True).order_by('building_code', 'room_number')
        self.fields['asset'].required = False
        self.fields['issue_photo'].required = False

        if 'room' in self.data:
            try:
                room_id = int(self.data.get('room'))
                self.fields['asset'].queryset = Asset.objects.filter(room_id=room_id)
            except (ValueError, TypeError):
                self.fields['asset'].queryset = Asset.objects.none()
        elif self.instance.pk and self.instance.room:
            self.fields['asset'].queryset = self.instance.room.assets.all()
        else:
            self.fields['asset'].queryset = Asset.objects.all()


class TicketStatusUpdateForm(forms.Form):
    status = forms.ChoiceField(
        choices=MaintenanceRequest.Status.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain what work was performed or why the status was changed...'
        })
    )
    resolution_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Provide final resolution details (required when setting status to RESOLVED)...'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        resolution_notes = cleaned_data.get('resolution_notes')
        if status in [MaintenanceRequest.Status.RESOLVED, MaintenanceRequest.Status.CLOSED] and not resolution_notes:
            self.add_error('resolution_notes', "Resolution notes are required when resolving or closing a maintenance request.")
        return cleaned_data


class TicketAssignForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=[User.Role.TECHNICIAN, User.Role.MANAGER, User.Role.ADMIN]),
        required=False,
        empty_label="-- Unassigned --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    priority = forms.ChoiceField(
        choices=MaintenanceRequest.Priority.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    status = forms.ChoiceField(
        choices=MaintenanceRequest.Status.choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Optional internal notes about triage or assignment instructions...'
        })
    )
