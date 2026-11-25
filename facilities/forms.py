from django import forms
from .models import Room, Asset


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['building_name', 'building_code', 'floor', 'room_number', 'room_type', 'capacity', 'is_active']
        widgets = {
            'building_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Science & Engineering Complex'}),
            'building_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SEC'}),
            'floor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1st Floor or 2'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 101'}),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ['room', 'name', 'asset_tag', 'category', 'status', 'installed_on', 'notes']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Overhead 4K Laser Projector'}),
            'asset_tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AST-SEC101-01'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'installed_on': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional asset details or vendor info'}),
        }

