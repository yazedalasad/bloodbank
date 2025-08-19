from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date, timedelta

from django.db import models
from django.utils import timezone
from datetime import date
from django.core.validators import EmailValidator, RegexValidator
from pydantic import ValidationError
from django.db.models import Sum ,Max
class Donor(models.Model):
    # ===== Personal Information =====
    BLOOD_TYPES = [
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-'),
    ]
    
    # Identification
    national_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="תעודת זהות",
        validators=[RegexValidator(r'^\d{9}$', 'תעודת זהות חייבת להכיל 9 ספרות')],
        null=True,
        blank=True,
    )
    
    

    # Personal Details
    first_name = models.CharField(max_length=100, verbose_name="שם פרטי",
        null=True,
        blank=True,)
    last_name = models.CharField(max_length=100, verbose_name="שם משפחה",
        null=True,
        blank=True,)
    date_of_birth = models.DateField(
        verbose_name="תאריך לידה",
        help_text="פורמט: YYYY-MM-DD",
        null=True,
        blank=True,
    )
    blood_type = models.CharField(
        max_length=3,
        choices=BLOOD_TYPES,
        verbose_name="סוג דם",
        null=True,
        blank=True,
    )

    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?0\d{9}$',
        message="מספר טלפון חייב להיות בפורמט: '+972501234567'"
    )
    phone_number = models.CharField(
        max_length=13,
        validators=[phone_regex],
        verbose_name="טלפון",
        unique=True,
        null=True,
        blank=True,
    )
    
    email = models.EmailField(
        verbose_name="אימייל",
        validators=[EmailValidator()],
        blank=True,
        null=True
    )

    # ===== Health/Lifestyle =====
    SMOKING_CHOICES = [
        ('never', 'לא מעשן'), ('former', 'עישן בעבר'),
        ('light', 'מעשן קל (עד 5/יום)'), ('heavy', 'מעשן כבד (5+/יום)')
    ]
    smoking_status = models.CharField(
        max_length=10,
        choices=SMOKING_CHOICES,
        default='never',
        verbose_name="עישון"
    )
    
    ALCOHOL_CHOICES = [
        ('never', 'לא שותה'), ('social', 'באירועים'),
        ('weekly', 'מספר פעמים בשבוע'), ('daily', 'יומי')
    ]
    alcohol_use = models.CharField(
        max_length=10,
        choices=ALCOHOL_CHOICES,
        default='never',
        verbose_name="אלכוהול"
    )

    # ===== System Fields =====
    

    class Meta:
        verbose_name = "תורם"
        verbose_name_plural = "תורמים"
        ordering = ['last_name', 'first_name']

    @property
    def age(self):
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    # In your Donor model
    @property
    def total_donations(self):
       return self.donations.aggregate(total=Sum('volume_ml'))['total'] or 0

    @property 
    def last_donation_date(self):
         last = self.donations.order_by('-donation_date').first()
         return last.donation_date if last else None

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.national_id})"

    def clean(self):
        # Validate national ID format (Israeli ID)
        if len(self.national_id) != 9 or not self.national_id.isdigit():
            raise ValidationError("תעודת זהות חייבת להכיל 9 ספרות")
        
class Donation(models.Model):
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name='donations', verbose_name="תורם")
    donation_date = models.DateField(verbose_name="תאריך תרומה", default=date.today)
    volume_ml = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(350), MaxValueValidator(500)],
        verbose_name="נפח (מ\"ל)",
        default=450
    )
    notes = models.TextField(blank=True, verbose_name="הערות")
    is_approved = models.BooleanField(default=True, verbose_name="אושר")
    
    class Meta:
        verbose_name = "תרומת דם"
        verbose_name_plural = "תרומות דם"
        ordering = ['-donation_date']
    
    def save(self, *args, **kwargs):
        # Auto-block donors who donated <56 days ago
        last_donation = Donation.objects.filter(
            donor=self.donor,
            donation_date__lt=self.donation_date
        ).order_by('-donation_date').first()
        
        if last_donation and (self.donation_date - last_donation.donation_date) < timedelta(days=56):
            self.is_approved = False
            self.notes = f"תרומה מוקדמת מדי. תרם לאחרונה ב-{last_donation.donation_date}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.donor} - {self.donation_date}"

from django.db import models
from django.utils import timezone
from .models import Donor

class BloodRequest(models.Model):
    # ===== Blood Type Choices =====
    BLOOD_TYPES = Donor.BLOOD_TYPES
    
    # ===== Priority Levels =====
    PRIORITY_CHOICES = [
        ('normal', 'בקשה רגילה'),
        ('urgent', 'דחוף'),
        ('critical', 'מצב קריטי (חירום)'),
    ]
    
    # ===== Core Fields =====
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="דחיפות"
    )
    
    patient_name = models.CharField(
        max_length=120,
        verbose_name="שם המטופל"
    )
    
    blood_type_needed = models.CharField(
        max_length=3,
        choices=BLOOD_TYPES,
        verbose_name="סוג דם נדרש"
    )
    
    units_needed = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="יחידות נדרשות",
        help_text="מקסימום 10 יחידות לבקשה"
    )
    
    emergency = models.BooleanField(
        default=False,
        verbose_name="בקשה דחופה?"
    )
    
    date_requested = models.DateTimeField(
        default=timezone.now,
        verbose_name="תאריך בקשה"
    )
    
    fulfilled = models.BooleanField(
        default=False,
        verbose_name="מולא?"
    )
    
    # ===== Automatic Methods =====
    def __str__(self):
        return f"{self.patient_name} - {self.get_blood_type_needed_display()} ({self.units_needed} יחידות)"
    
    class Meta:
        verbose_name = "בקשת דם"
        verbose_name_plural = "בקשות דם"
        ordering = ['-date_requested']
    
    @property
    def status(self):
        if self.fulfilled:
            return "סופק"
        elif self.emergency:
            return "דחוף"
        return "ממתין"