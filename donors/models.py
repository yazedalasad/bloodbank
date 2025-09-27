# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Sum, Max
from django.utils.translation import gettext_lazy as _

# =====================
# HELPER FUNCTIONS & VALIDATORS
# =====================
from django.core.exceptions import ValidationError

def validate_israeli_id(value):
    """
    Validates Israeli ID number (Tz) by checking:
    - Must be exactly 9 digits
    - Must contain only digits
    """
    value = str(value).strip()
    
    if not value.isdigit():
        raise ValidationError(_("תעודת זהות חייבת להכיל רק ספרות"))
    
    if len(value) != 9:
        raise ValidationError(_("תעודת זהות חייבת להיות בת 9 ספרות"))

def validate_israeli_phone(value):
    """
    Validates Israeli phone number format.
    Accepts formats: 05X-XXXXXXX, +9725X-XXXXXXX, 05XXXXXXXX
    """
    import re
    pattern = r'^(?:\+972|0)(?:\-)?5[02-9](?:\-)?\d{7}$'
    if not re.match(pattern, value.strip()):
        raise ValidationError(_(
            "מספר טלפון חייב להיות בפורמט ישראלי תקני: "
            "'05X-XXXXXXX', '+9725X-XXXXXXX' או '05XXXXXXXX'"
        ))
# Add this to your forms.py
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_email(value):
    """
    Simple email validation function that checks:
    1. Basic email format
    2. Common disposable email domains
    """
    if not value:
        return value
    
    value = value.strip()
    
    # Basic email format validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, value):
        raise ValidationError(_("כתובת האימייל אינה בפורמט תקין. אנא הזן כתובת בסגנון name@example.com"))
    
    # Check for disposable email domains
    domain = value.split('@')[1].lower()
    
    disposable_domains = [
        'tempmail.com', 'disposable.com', 'throwaway.com', 'temp-mail.org',
        'guerrillamail.com', 'mailinator.com', '10minutemail.com', 'yopmail.com',
        'fakeinbox.com', 'trashmail.com'
    ]
    
    if domain in disposable_domains:
        raise ValidationError(_("לא ניתן להשתמש בכתובת אימייל זמנית. אנא השתמש בכתובת אימייל קבועה."))
    
    return value
# =====================
# USER PROFILE (Role-Based Access)
# =====================
class Profile(models.Model):
    """
    Extends Django's User model to support role-based permissions.
    Each user is either a 'doctor' or 'patient'.
    
    Key Features:
    - Role assignment for access control
    - Phone number storage
    - Creation timestamp
    """
    ROLE_CHOICES = [
        ('doctor', _('Doctor')),
        ('patient', _('Patient')),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name=_("User")
    )
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES,
        verbose_name=_("Role")
    )

    national_id = models.CharField(
        max_length=9,
        blank=True,  # Make it optional if needed, or set required=False in the form
        null=True,
        verbose_name=_("National ID"),
        validators=[validate_israeli_id],  # Use the same validator as the Donor model
        help_text=_("9 digits without dashes")
    )
    phone_number = models.CharField(
        max_length=15, 
        blank=True,
        null=True,
        verbose_name=_("Phone Number"),
        validators=[RegexValidator(
            r'^(\+972|0)(\-)?5[02-9](\-)?\d{7}$',
            _("מספר טלפון לא תקין")
        )]
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    
    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()}"

    @property
    def is_doctor(self):
        """Check if user has doctor role"""
        return self.role == 'doctor'
    
    @property
    def is_patient(self):
        """Check if user has patient role"""
        return self.role == 'patient'


# Automatically create and save profile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create profile when new user is created"""
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is updated"""
    instance.profile.save()


# =====================
# DONOR MODEL (Patient + Donor)
# =====================
class Donor(models.Model):
    """
    Represents a blood donor. Can be linked to a User (for patients who are also donors).
    Includes personal, contact, health, and donation history data.
    
    Key Features:
    - Comprehensive personal information
    - Detailed health and lifestyle data
    - Donation history tracking
    - Automatic eligibility checks
    - Israeli-specific validation
    """
    # Blood Type Choices
    BLOOD_TYPES = [
        ('A+', _('A+')), ('A-', _('A-')), ('B+', _('B+')), ('B-', _('B-')),
        ('AB+', _('AB+')), ('AB-', _('AB-')), ('O+', _('O+')), ('O-', _('O-')),
    ]
    
    # Health Status Choices
    HEALTH_STATUS_CHOICES = [
        ('excellent', _(' מצויין')),
        ('good', _('טוב')),
        ('fair', _('סביר')),
        ('poor', _('לא טוב')),
    ]
    
    # Smoking & Alcohol Status
    SMOKING_CHOICES = [
        ('never', _('לא מעשן')),
        ('former', _('עישן בעבר')),
        ('light', _('מעשן קל (עד 5/יום)')),
        ('heavy', _('מעשן כבד (5+/יום)'))
    ]
    
    ALCOHOL_CHOICES = [
        ('never', _('לא שותה')),
        ('social', _('באירועים')),
        ('weekly', _('מספר פעמים בשבוע')),
        ('daily', _('יומי'))
    ]

    # Identification
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='donor',
        verbose_name=_("User Account"),
        help_text=_("מקושר לחשבון משתמש (אופציונלי)")
    )
    
    national_id = models.CharField(
        max_length=9,
        unique=True,
        verbose_name=_("תעודת זהות"),
        validators=[validate_israeli_id],
        help_text=_("9 ספרות ללא מקפים")
    )
    
    # Personal Details
    first_name = models.CharField(
        max_length=100, 
        verbose_name=_("שם פרטי")
    )
    
    last_name = models.CharField(
        max_length=100, 
        verbose_name=_("שם משפחה")
    )
    
    date_of_birth = models.DateField(
        verbose_name=_("תאריך לידה"),
        help_text=_("פורמט: YYYY-MM-DD")
    )
    
    blood_type = models.CharField(
        max_length=3,
        choices=BLOOD_TYPES,
        verbose_name=_("סוג דם")
    )
    
    health_status = models.CharField(
        max_length=10,
        choices=HEALTH_STATUS_CHOICES,
        default='good',
        verbose_name=_("מצב בריאות")
    )

    # Contact Information
    phone_number = models.CharField(
        max_length=15,
        validators=[validate_israeli_phone],
        verbose_name=_("טלפון"),
        unique=True,
        help_text=_("פורמט: 05X-XXXXXXX")
    )
    
    email = models.EmailField(
        verbose_name=_("אימייל"),
        validators=[EmailValidator()],
        blank=True,
        null=True
    )
    
    address = models.TextField(
        verbose_name=_("כתובת"),
        blank=True,
        null=True
    )

    # Health/Lifestyle
    smoking_status = models.CharField(
        max_length=10,
        choices=SMOKING_CHOICES,
        default='never',
        verbose_name=_("עישון")
    )
    
    alcohol_use = models.CharField(
        max_length=10,
        choices=ALCOHOL_CHOICES,
        default='never',
        verbose_name=_("אלכוהול")
    )
    
    # Medical History
    has_chronic_illness = models.BooleanField(
        default=False,
        verbose_name=_("חולה במחלות כרוניות")
    )
    
    chronic_illness_details = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("פרטי מחלות כרוניות"),
        help_text=_("פרט את סוג המחלות והטיפול")
    )
    
    last_medical_exam = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("תאריך בדיקה רפואית אחרונה"),
        help_text=_("תאריך הבדיקה הרפואית האחרונה - לא יכול להיות בעתיד")
    )

    # System Fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("נוצר ב")
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("עודכן ב")
    )
    
    class Meta:
        verbose_name = _("תורם")
        verbose_name_plural = _("תורמים")
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['blood_type']),
            models.Index(fields=['national_id']),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.national_id})"

    @property
    def age(self):
        """Calculate donor's age based on date of birth"""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    @property
    def total_donations(self):
        """Calculate total blood donated in milliliters"""
        return self.donations.aggregate(total=Sum('volume_ml'))['total'] or 0
    
    @property 
    def last_donation_date(self):
        """Get date of last donation"""
        last = self.donations.order_by('-donation_date').first()
        return last.donation_date if last else None
    
    @property
    def can_donate(self):
        """Check if donor can donate based on 56-day rule"""
        if not self.last_donation_date:
            return True
        
        days_since_last = (date.today() - self.last_donation_date).days
        return days_since_last >= 56
    
    @property
    def days_until_next_donation(self):
        """Calculate days remaining until next allowed donation"""
        if not self.last_donation_date:
            return 0
            
        days_passed = (date.today() - self.last_donation_date).days
        return max(0, 56 - days_passed)
    
    @property
    def total_donation_units(self):
        """Convert total ml to standard donation units (450ml = 1 unit)"""
        return round(self.total_donations / 450, 1)
    
    def clean(self):
        """Additional validation for donor model"""
        # Age validation (must be 18-65 for blood donation in Israel)
        if self.date_of_birth:
            donor_age = self.age
            if donor_age < 18:
                raise ValidationError(_("תורם חייב להיות מעל גיל 18"))
            if donor_age > 65:
                raise ValidationError(_("תורם לא יכול להיות מעל גיל 65"))
        
        # Chronic illness validation
        if self.has_chronic_illness and not self.chronic_illness_details:
            raise ValidationError(_(
                "יש לציין פרטי מחלות כרוניות אם סימנת שיש מחלות כרוניות"
            ))
        if self.last_medical_exam and self.last_medical_exam > date.today():
            raise ValidationError(_(
                "תאריך הבדיקה הרפואית לא יכול להיות בעתיד"
            ))

    def save(self, *args, **kwargs):
        """Custom save method with additional validation"""
        self.full_clean()
        super().save(*args, **kwargs)


# =====================
# DONATION MODEL
# =====================
class Donation(models.Model):
    """
    Records of blood donations made by donors.
    
    Key Features:
    - Automatic eligibility checks
    - Volume validation (350-500ml)
    - Approval workflow
    - Historical tracking
    """
    donor = models.ForeignKey(
        Donor, 
        on_delete=models.CASCADE, 
        related_name='donations',
        verbose_name=_("תורם")
    )
    
    donation_date = models.DateField(
        verbose_name=_("תאריך תרומה"),
        default=date.today
    )
    
    volume_ml = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(350), MaxValueValidator(500)],
        verbose_name=_("נפח (מ\"ל)"),
        default=450,
        help_text=_("נפח תרומה סטנדרטי: 450 מ\"ל")
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_("הערות"),
        help_text=_("הערות נוספות על התרומה")
    )
    
    is_approved = models.BooleanField(
        default=True,
        verbose_name=_("אושר"),
        help_text=_("האם התרומה אושרה על ידי הרופא")
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations_created',
        verbose_name=_("נוצר על ידי")
    )
    
    class Meta:
        verbose_name = _("תרומת דם")
        verbose_name_plural = _("תרומות דם")
        ordering = ['-donation_date']
        indexes = [
            models.Index(fields=['donation_date']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"{self.donor} - {self.donation_date} ({self.volume_ml} מ\"ל)"
    
    @property
    def donation_units(self):
        """Convert ml to standard donation units"""
        return round(self.volume_ml / 450, 1)
    
    @property
    def is_recent(self):
        """Check if donation was in the last 30 days"""
        return (date.today() - self.donation_date).days <= 30
    
    def save(self, *args, **kwargs):
        """
        Custom save method that:
        1. Checks donation eligibility (56-day rule)
        2. Sets approval status automatically
        3. Records creator if not specified
        """
        # Auto-block donors who donated <56 days ago
        last_donation = Donation.objects.filter(
            donor=self.donor,
            donation_date__lt=self.donation_date
        ).order_by('-donation_date').first()
        
        if last_donation and (self.donation_date - last_donation.donation_date) < timedelta(days=56):
            self.is_approved = False
            self.notes = _(
                f"תרומה מוקדמת מדי. תרם לאחרונה ב-{last_donation.donation_date}. "
                f"ניתן לתרום שוב החל מ-{last_donation.donation_date + timedelta(days=56)}"
            )
        
        # Set creator if not specified
        if not self.pk and not self.created_by:
            # Use the donor's user as creator if available
            if self.donor and self.donor.user:
                self.created_by = self.donor.user
        
        super().save(*args, **kwargs)


# =====================
# BLOOD REQUEST MODEL
# =====================
class BloodRequest(models.Model):

    """
    Records of blood requests made by patients or doctors.
    
    Key Features:
    - Priority-based fulfillment
    - Emergency handling
    - Status tracking
    - User attribution
    """
    # Blood Type Choices (same as Donor)
    BLOOD_TYPES = Donor.BLOOD_TYPES
    
    # Priority Levels
    PRIORITY_CHOICES = [
        ('normal', _('בקשה רגילה')),
        ('urgent', _('דחוף')),
        ('critical', _('מצב קריטי (חירום)')),
    ]
    
    # Core Fields
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name=_("דחיפות")
    )
    
    patient_name = models.CharField(
        max_length=120,
        verbose_name=_("שם המטופל")
    )
    
    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blood_requests',
        verbose_name=_("מבקש"),
        help_text=_("המשתמש שביצע את הבקשה")
    )
    
    blood_type_needed = models.CharField(
        max_length=3,
        choices=BLOOD_TYPES,
        verbose_name=_("סוג דם נדרש")
    )
    
    units_needed = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_("יחידות נדרשות"),
        help_text=_("מקסימום 10 יחידות לבקשה")
    )
    
    emergency = models.BooleanField(
        default=False,
        verbose_name=_("בקשה דחופה?"),
        help_text=_("סימון זה יגרום לשינוי סוג הדם ל-O- אוטומטית")
    )
    
    date_requested = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("תאריך בקשה")
    )
    
    fulfilled = models.BooleanField(
        default=False,
        verbose_name=_("מולא?")
    )
    
    fulfilled_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("תאריך מילוי")
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_("הערות"),
        help_text=_("הערות נוספות על הבקשה")
    )
    
    class Meta:
        verbose_name = _("בקשת דם")
        verbose_name_plural = _("בקשות דם")
        ordering = ['-date_requested']
        indexes = [
            models.Index(fields=['priority', 'fulfilled']),
            models.Index(fields=['blood_type_needed']),
        ]
    
    def __str__(self):
        return f"{self.patient_name} - {self.get_blood_type_needed_display()} ({self.units_needed} יחידות)"
    
   
    @property
    def status(self):
        """Get human-readable status of the request"""
        if self.fulfilled:
            return _("סופק")
        elif self.emergency:
            return _("דחוף")
        return _("ממתין")
    
    @property
    def is_overdue(self):
        """Check if request is overdue (normal requests > 7 days)"""
        if self.fulfilled:
            return False
        return (timezone.now() - self.date_requested) > timedelta(days=7)
    
    def save(self, *args, **kwargs):
        """Custom save method with business logic"""
        # Emergency requests automatically use O- blood
        if self.emergency and self.blood_type_needed != 'O-':
            self.blood_type_needed = 'O-'
            self.priority = 'critical'
            self.notes = _("בקשה חירום - שונו אוטומטית לסוג דם O-") + "\n" + (self.notes or "")
        
        # Set fulfilled date when status changes
        if self.fulfilled and not self.fulfilled_date:
            self.fulfilled_date = timezone.now()
        
        super().save(*args, **kwargs)


# models.py (add this new model at the end)
class UserReport(models.Model):
    """Model to store user PDF reports without modifying Profile"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name=_("User")
    )
    
    report_type = models.CharField(
        max_length=20,
        choices=[('doctor', _('Doctor Report')), ('patient', _('Patient Report'))],
        verbose_name=_("Report Type")
    )
    
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Generated At")
    )
    
    pdf_file = models.FileField(
        upload_to='user_reports/%Y/%m/%d/',
        verbose_name=_("PDF File")
    )
    
    email_sent = models.BooleanField(
        default=False,
        verbose_name=_("Email Sent")
    )
    
    class Meta:
        verbose_name = _("User Report")
        verbose_name_plural = _("User Reports")
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_report_type_display()} - {self.generated_at}"
    
    def get_download_url(self):
        """Get download URL for the PDF"""
        return self.pdf_file.url if self.pdf_file else None