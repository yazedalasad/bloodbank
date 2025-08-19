from django import forms
from django.utils import timezone
from .models import Donor, Donation, BloodRequest
from django.core.exceptions import ValidationError

class DonorForm(forms.ModelForm):
    class Meta:
        model = Donor
        fields = '__all__'
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'national_id': 'תעודת זהות',
            'blood_type': 'סוג דם',
            'smoking_status': 'סטטוס עישון',
            'alcohol_use': 'צריכת אלכוהול',
        }

    def clean_national_id(self):
        id = self.cleaned_data['national_id']
        if len(id) not in [8, 9]:
            raise ValidationError("תעודת זהות חייבת להכיל 8-9 ספרות")
        return id

class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['donor','donation_date', 'volume_ml', 'notes']
        widgets = {
            'donor': forms.Select(attrs={'class': 'form-select'}),
            'donation_date': forms.DateInput(attrs={'type': 'date'}),
            'volume_ml': forms.NumberInput(attrs={'min': 350, 'max': 500}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'הערות רפואיות רלוונטיות...'}),
        }
        labels = {
            'volume_ml': 'נפח תרומה (מ"ל)',
            'notes': 'הערות',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['donor'].queryset = Donor.objects.all()

class BloodRequestForm(forms.ModelForm):
    class Meta:
        model = BloodRequest
        fields = ['patient_name', 'blood_type_needed', 'units_needed', 'priority', 'emergency']
        widgets = {
            'patient_name': forms.TextInput(attrs={'placeholder': 'שם מלא של המטופל'}),
            'units_needed': forms.NumberInput(attrs={'min': 1, 'max': 10}),
            'emergency': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'blood_type_needed': 'סוג דם נדרש',
            'units_needed': 'מספר יחידות',
            'priority': 'דחיפות',
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('emergency') and cleaned_data.get('priority') != 'critical':
            self.add_error('priority', "בקשה דחופה חייבת להיות מסומנת כמצב קריטי")
        return cleaned_data