# forms.py
from datetime import timedelta
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
from .models import Donor, Donation, BloodRequest, Profile
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Donor, Donation, BloodRequest, Profile, validate_israeli_id, validate_email
class DonorForm(forms.ModelForm):
    """
    Form for creating and updating donor profiles.
    Handles all validation rules including Israeli ID validation,
    age restrictions, and donation eligibility.
    """
    # Custom validation messages
    NATIONAL_ID_ERROR = _(
        "תעודת זהות חייבת להיות מספר בן 9 ספרות תקני. "
        "אנא בדוק את התעודה ונסה שוב."
    )
    AGE_ERROR = _(
        "לפי חוקי מדינת ישראל, גיל התורם חייב להיות בין 18 ל-65. "
        "לא ניתן לרשום תורם מחוץ לטווח גילאים זה."
    )
    
    class Meta:
        model = Donor
        fields = [
            'first_name', 'last_name', 'national_id', 'date_of_birth',
            'blood_type', 'phone_number', 'email', 'address',
            'health_status', 'smoking_status', 'alcohol_use',
            'has_chronic_illness', 'chronic_illness_details', 'last_medical_exam'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'last_medical_exam': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'chronic_illness_details': forms.Textarea(
                attrs={'rows': 3, 'placeholder': _('פרט את סוג המחלות והטיפול...')}
            ),
            'address': forms.Textarea(
                attrs={'rows': 2, 'placeholder': _('רחוב, מספר, עיר...')}
            ),
            'phone_number': forms.TextInput(
                attrs={'placeholder': _('05X-XXXXXXX')}
            ),
            'email': forms.EmailInput(
                attrs={'placeholder': _('example@email.com')}
            )
        }
        labels = {
            'national_id': _('תעודת זהות'),
            'blood_type': _('סוג דם'),
            'smoking_status': _('סטטוס עישון'),
            'alcohol_use': _('צריכת אלכוהול'),
            'health_status': _('מצב בריאות'),
            'has_chronic_illness': _('חולה במחלות כרוניות'),
            'chronic_illness_details': _('פרטי מחלות כרוניות'),
            'last_medical_exam': _('תאריך בדיקה רפואית אחרונה'),
            'address': _('כתובת'),
        }
        help_texts = {
            'national_id': _('9 ספרות ללא מקפים'),
            'phone_number': _('פורמט: 05X-XXXXXXX'),
            'blood_type': _('סוג הדם שלך כפי שמופיע בתעודה הרפואית'),
            'has_chronic_illness': _('סמן אם יש לך מחלות כרוניות שעשויות להשפיע על היכולת לתרום'),
            'last_medical_exam': _('תאריך הבדיקה הרפואית האחרונה שלך')
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make required fields visually clear
        for field in self.fields:
            if self.fields[field].required:
                self.fields[field].widget.attrs.update({'required': 'required'})
        
        # Customize choices display
        self.fields['blood_type'].choices = [('', _('בחר סוג דם'))] + list(self.fields['blood_type'].choices)[1:]
        self.fields['health_status'].choices = [('', _('בחר מצב בריאות'))] + list(self.fields['health_status'].choices)[1:]

    def clean_national_id(self):
        """Validate Israeli ID by checking length and numeric format only."""
        national_id = self.cleaned_data.get('national_id', '').strip()

        if not national_id:
           raise ValidationError(self.NATIONAL_ID_ERROR)

        if not national_id.isdigit():
           raise ValidationError(self.NATIONAL_ID_ERROR)

        if len(national_id) != 9:  
           raise ValidationError(self.NATIONAL_ID_ERROR)
        
        return national_id.zfill(9)

    def clean_date_of_birth(self):
        """Validate age is between 18-65 per Israeli regulations"""
        date_of_birth = self.cleaned_data.get('date_of_birth')
        
        if date_of_birth:
            today = timezone.now().date()
            age = today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
            )
            
            if age < 18:
                raise ValidationError(self.AGE_ERROR)
            if age > 65:
                raise ValidationError(self.AGE_ERROR)
                
        return date_of_birth

    def clean_chronic_illness_details(self):
        """Require details if chronic illness is marked"""
        has_chronic = self.cleaned_data.get('has_chronic_illness', False)
        details = self.cleaned_data.get('chronic_illness_details', '').strip()
        
        if has_chronic and not details:
            raise ValidationError(_(
                "יש לציין פרטי מחלות כרוניות אם סימנת שיש מחלות כרוניות"
            ))
            
        return details

    def clean(self):
     cleaned_data = super().clean()
    
     # Phone number validation
     phone = cleaned_data.get('phone_number')
     if phone is not None:
        phone = str(phone).strip()
        clean_phone = phone.replace('-', '').replace(' ', '')
        if clean_phone:
            if not (clean_phone.startswith('05') and len(clean_phone) == 10):
                raise ValidationError(_(
                    "מספר טלפון חייב להיות בפורמט ישראלי תקני: 05X-XXXXXXX"
                ))
            cleaned_data['phone_number'] = clean_phone
     # If phone is None or empty, leave as-is (let model handle blank=True/False)

     # Email validation
     email = cleaned_data.get('email')
     if email is not None:
        email = str(email).strip()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError(_("כתובת אימייל לא תקינה"))
            cleaned_data['email'] = email
        else:
            cleaned_data['email'] = ''  # Normalize empty string
     else:
        cleaned_data['email'] = ''

     return cleaned_data


class DonationForm(forms.ModelForm):
    """
    Form for recording blood donations.
    Includes validation for the 56-day donation rule and proper volume.
    """
    ELIGIBILITY_ERROR = _(
        "לא ניתן לתרום דם לפני 56 ימים מהתרומה הקודמת. "
        "תאריך התרומה האחרון: {last_donation}. "
        "ניתן לתרום שוב החל מ-{next_donation}."
    )
    
    class Meta:
        model = Donation
        fields = ['donor', 'donation_date', 'volume_ml', 'notes']
        widgets = {
            'donor': forms.Select(attrs={'class': 'form-select'}),
            'donation_date': forms.DateInput(attrs={'type': 'date'}),
            'volume_ml': forms.NumberInput(attrs={'min': 350, 'max': 500}),
            'notes': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': _('הערות רפואיות, תסמינים, וכו\'...')
            }),
        }
        labels = {
            'volume_ml': _('נפח תרומה (מ"ל)'),
            'notes': _('הערות'),
        }
        help_texts = {
            'donation_date': _('תאריך התרומה (ברירת מחדל: היום)'),
            'volume_ml': _('נפח תרומה סטנדרטי הוא 450 מ"ל'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default date to today
        if not self.instance.pk:
            self.fields['donation_date'].initial = timezone.now().date()
        
        # Customize donor queryset
        self.fields['donor'].queryset = Donor.objects.all().order_by('last_name', 'first_name')
        self.fields['donor'].empty_label = _('בחר תורם')

    def clean(self):
        """Validate donation eligibility based on 56-day rule"""
        cleaned_data = super().clean()
        donor = cleaned_data.get('donor')
        donation_date = cleaned_data.get('donation_date')
        
        if donor and donation_date:
            # Check last donation
            last_donation = Donation.objects.filter(
                donor=donor,
                donation_date__lt=donation_date
            ).order_by('-donation_date').first()
            
            if last_donation:
                days_since_last = (donation_date - last_donation.donation_date).days
                
                if days_since_last < 56:
                    next_donation = last_donation.donation_date + timedelta(days=56)
                    error_msg = self.ELIGIBILITY_ERROR.format(
                        last_donation=last_donation.donation_date.strftime('%d/%m/%Y'),
                        next_donation=next_donation.strftime('%d/%m/%Y')
                    )
                    raise ValidationError(error_msg)
        
        return cleaned_data


class BloodRequestForm(forms.ModelForm):
    """
    Form for requesting blood units.
    Handles emergency requests and priority validation.
    """
    EMERGENCY_ERROR = _(
        "בקשה דחופה חייבת להיות מסומנת כמצב קריטי. "
        "בקשות חירום ישתמשו אוטומטית בסוג דם O-."
    )
    
    class Meta:
        model = BloodRequest
        fields = ['patient_name', 'blood_type_needed', 'units_needed', 'priority', 'emergency', 'notes']
        widgets = {
            'patient_name': forms.TextInput(attrs={'placeholder': _('שם מלא של המטופל')}),
            'units_needed': forms.NumberInput(attrs={'min': 1, 'max': 10}),
            'emergency': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('סיבות לבקשה דחופה, פרטים רפואיים רלוונטיים...')
            }),
        }
        labels = {
            'blood_type_needed': _('סוג דם נדרש'),
            'units_needed': _('מספר יחידות'),
            'priority': _('דחיפות'),
            'emergency': _('מצב חירום?'),
            'notes': _('הערות'),
        }
        help_texts = {
            'units_needed': _('מקסימום 10 יחידות לבקשה'),
            'emergency': _('סימון זה יגרום לשינוי סוג הדם ל-O- אוטומטית'),
            'blood_type_needed': _('סוג דם נדרש למטופל'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Customize choices display
        self.fields['blood_type_needed'].choices = [('', _('בחר סוג דם'))] + list(self.fields['blood_type_needed'].choices)[1:]
        self.fields['priority'].choices = [('', _('בחר דחיפות'))] + list(self.fields['priority'].choices)[1:]

    def clean(self):
        """Validate emergency request logic"""
        cleaned_data = super().clean()
        emergency = cleaned_data.get('emergency', False)
        priority = cleaned_data.get('priority', '')
        
        # Emergency requests must be critical priority
        if emergency and priority != 'critical':
            self.add_error('priority', self.EMERGENCY_ERROR)
        
        # Emergency requests automatically use O- blood
        if emergency:
            cleaned_data['blood_type_needed'] = 'O-'
        
        return cleaned_data

    def save(self, commit=True):
        """Set requested_by field to current user"""
        instance = super().save(commit=False)
        if self.user:
            instance.requested_by = self.user
        if commit:
            instance.save()
        return instance


class DoctorRegistrationForm(UserCreationForm):
    """
    Form for doctors to register new accounts.
    Includes all necessary profile information.
    """
    email = forms.EmailField(
        required=True,
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={'placeholder': _('example@email.com')})
    )
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': _('שם פרטי')})
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': _('שם משפחה')})
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        validators=[RegexValidator(
            r'^(\+972|0)(\-)?5[02-9](\-)?\d{7}$',
            _('מספר טלפון לא תקין')
        )],
        widget=forms.TextInput(attrs={'placeholder': _('05X-XXXXXXX')})
    )
    national_id = forms.CharField(
        max_length=9,
        required=True,  # Or False, depending on your requirement
        validators=[validate_israeli_id],  # Import this function if needed
        label=_('תעודת זהות'),
        help_text=_('9 ספרות ללא מקפים'),
        widget=forms.TextInput(attrs={'placeholder': _('הזן 9 ספרות')})
    )
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': _('שם משתמש')}), 
        }
        labels = {
            'username': _('שם משתמש'),
            'email': _('אימייל'),
            'first_name': _('שם פרטי'),
            'last_name': _('שם משפחה'),
            'password1': _('סיסמה'),
            'password2': _('אימות סיסמה'),
        }
        help_texts = {
            'username': _('נדרש. עד 150 תווים, רק אותיות, מספרים ו@/./+/-/_'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update password help text
        self.fields['password1'].help_text = _(
            "הסיסמה לא יכולה להיות דומה למידע אישי שלך.<br>"
            "הסיסמה חייבת להכיל לפחות 8 תווים.<br>"
            "הסיסמה לא יכולה להיות נפוצה או פשוטה מדי.<br>"
            "הסיסמה לא יכולה להיות כולה מספרים."
        )
        
        # Add required attribute to fields
        for field_name in self.fields:
            if self.fields[field_name].required:
                self.fields[field_name].widget.attrs['required'] = 'required'

    def save(self, commit=True):
        """Create user and profile with doctor role"""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
    
        if commit:
         user.save()
        
         # FIRST, check if a profile was already created by the signal
         if hasattr(user, 'profile'):
            # If profile exists (created by signal), update it to doctor
            user.profile.role = 'doctor'
            user.profile.phone_number = self.cleaned_data['phone_number']
            user.profile.national_id = self.cleaned_data['national_id']
            user.profile.save()
         else:
            # If no profile exists, create it as doctor
            Profile.objects.create(
                user=user,
                role='doctor',
                phone_number=self.cleaned_data['phone_number'],
                national_id=self.cleaned_data['national_id']
            )

        return user


class PatientRegistrationForm(UserCreationForm):
    """
    Form for patients to register new accounts.
    Includes option to register as a donor during signup.
    """

    email = forms.EmailField(
        required=True,
        validators=[EmailValidator()],
        widget=forms.EmailInput(attrs={'placeholder': _('example@email.com')})
    )
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': _('שם פרטי')})
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': _('שם משפחה')})
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        validators=[RegexValidator(
            r'^(\+972|0)(\-)?5[02-9](\-)?\d{7}$',
            _('מספר טלפון לא תקין')
        )],
        widget=forms.TextInput(attrs={'placeholder': _('05X-XXXXXXX')})
    )
    is_donor = forms.BooleanField(
        required=False,
        initial=False,
        label=_('אני תורם דם'),
        help_text=_('סמן אם ברצונך להירשם גם כמתורם דם')
    )
    national_id = forms.CharField(
        max_length=9,
        required=True,  # Or False, depending on your requirement
        validators=[validate_israeli_id],  # Import this function if needed
        label=_('תעודת זהות'),
        help_text=_('9 ספרות ללא מקפים'),
        widget=forms.TextInput(attrs={'placeholder': _('הזן 9 ספרות')})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': _('שם משתמש')}), 
        }
        labels = {
            'username': _('שם משתמש'),
            'email': _('אימייל'),
            'first_name': _('שם פרטי'),
            'last_name': _('שם משפחה'),
            'password1': _('סיסמה'),
            'password2': _('אימות סיסמה'),
        }
        help_texts = {
            'username': _('נדרש. עד 150 תווים, רק אותיות, מספרים ו@/./+/-/_'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update password help text
        self.fields['password1'].help_text = _(
            "הסיסמה לא יכולה להיות דומה למידע אישי שלך.<br>"
            "הסיסמה חייבת להכיל לפחות 8 תווים.<br>"
            "הסיסמה לא יכולה להיות נפוצה או פשוטה מדי.<br>"
            "הסיסמה לא יכולה להיות כולה מספרים."
        )
        
        # Add required attribute to fields
        for field_name in self.fields:
            if self.fields[field_name].required:
                self.fields[field_name].widget.attrs['required'] = 'required'

    def save(self, commit=True):
     """Create user, profile, and optional donor profile"""
     user = super().save(commit=False)
     user.email = self.cleaned_data['email']
     user.first_name = self.cleaned_data['first_name']
     user.last_name = self.cleaned_data['last_name']
    
     if commit:
        user.save()
        # Use update_or_create to prevent IntegrityError
        Profile.objects.update_or_create(
            user=user,
            defaults={
                'role': 'patient',
                'phone_number': self.cleaned_data['phone_number'],
                'national_id': self.cleaned_data['national_id'],
            }
        )
        
        # Create donor profile if requested
        if self.cleaned_data.get('is_donor', False):
            Donor.objects.update_or_create(
                user=user,
                defaults={
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone_number': self.cleaned_data['phone_number'],
                    'email': user.email,
                    # Other fields can remain None initially
                }
            )
     return user