from django.shortcuts import render, redirect

from django.db.models import Sum,Max
from .models import Donor, Donation, BloodRequest
from .forms import DonorForm, DonationForm, BloodRequestForm
from .decorators import doctor_required, patient_required  
from django.contrib.auth.decorators import login_required

# Blood type compatibility map (Hebrew labels)
COMPATIBLE = {
    'O-': ['O-'],
    'O+': ['O-', 'O+'],
    'A-': ['O-', 'A-'],
    'A+': ['O-', 'O+', 'A-', 'A+'],
    'B-': ['O-', 'B-'],
    'B+': ['O-', 'O+', 'B-', 'B+'],
    'AB-': ['O-', 'A-', 'B-', 'AB-'],
    'AB+': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
}

from django.db.models import Count, Sum, Max, Q
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Donor
@doctor_required
def donor_list(request):
    # Get search parameters
    search_query = request.GET.get('q', '')
    blood_type_filter = request.GET.get('blood_type', '')
    
    # Base queryset with annotations
    donors = Donor.objects.annotate(
        total_donated=Sum('donations__volume_ml'),
        last_donation=Max('donations__donation_date')
    ).order_by('last_name', 'first_name')
    
    # Apply filters
    if search_query:
        donors = donors.filter(national_id__icontains=search_query)
    
    # Get blood type distribution BEFORE applying blood type filter
    # This ensures we calculate percentages against all donors, not filtered ones
    all_blood_types = [choice[0] for choice in Donor.BLOOD_TYPES]
    
    # Get counts for ALL donors (before blood type filter)
    base_queryset = Donor.objects.all()
    if search_query:
        base_queryset = base_queryset.filter(national_id__icontains=search_query)
    
    blood_type_counts = base_queryset.values('blood_type').annotate(
        count=Count('id')
    )
    
    # Create a dictionary for blood type counts
    count_dict = {item['blood_type']: item['count'] for item in blood_type_counts}
    
    # Calculate total donors (before blood type filter)
    total_for_percentage = base_queryset.count()
    
    # Calculate percentages
    blood_type_stats = []
    for blood_type in all_blood_types:
        count = count_dict.get(blood_type, 0)
        percentage = (count / total_for_percentage * 100) if total_for_percentage > 0 else 0
        blood_type_stats.append({
            'blood_type': blood_type,
            'count': count,
            'percentage': round(percentage, 1)
        })
    
    # Sort by count descending
    blood_type_stats.sort(key=lambda x: x['count'], reverse=True)
    
    # NOW apply blood type filter to the main queryset
    if blood_type_filter:
        donors = donors.filter(blood_type=blood_type_filter)
    
    # Get final count for pagination and stats
    total_donors = donors.count()
    
    # Prepare donor stats
    donor_stats = {
        'total': total_donors,
        'o_negative': donors.filter(blood_type='O-').count(),
        'blood_type_distribution': blood_type_stats  # This shows distribution of ALL blood types
    }
    
    # Pagination
    paginator = Paginator(donors, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'donors': page_obj,
        'donor_stats': donor_stats,
        'blood_types': Donor.BLOOD_TYPES,
        'search_query': search_query,
        'blood_type_filter': blood_type_filter,
    }
    
    return render(request, 'donors/donor_list.html', context)
from django.contrib.auth.decorators import login_required
from .decorators import doctor_required  # Or use login_required + role check



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.contrib import messages
from .forms import DonorForm
from .models import Donor

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Donor, Profile  # Make sure Profile is imported
from .forms import DonorForm

@login_required
def donor_create(request):

    
    # Determine user role
    try:
        is_doctor = request.user.profile.role == 'doctor'
    except (AttributeError, Profile.DoesNotExist):
        messages.error(request, "פרופיל המשתמש לא נמצא. פנה לתמיכה.")
        return redirect('home')

    if request.method == 'POST':
        form = DonorForm(request.POST)

        if form.is_valid():
            try:
                donor = form.save(commit=False)

                # 🔐 For patients: enforce personal data from user/profile (security)
                if not is_doctor:
                    donor.first_name = request.user.first_name
                    donor.last_name = request.user.last_name
                    donor.phone_number = request.user.profile.phone_number
                    donor.email = request.user.email
                    donor.national_id = request.user.profile.national_id
                    donor.user = request.user  # Link donor to user

                donor.save()
                messages.success(request, f"התורם {donor.first_name} {donor.last_name} נוסף בהצלחה!")
                return redirect('donor_list')

            except Exception as e:
                messages.error(request, f"שגיאה בעת שמירת התורם: {str(e)}")
        else:
            messages.error(request, "נא לתקן את השגיאות בטופס.")

    else:
        # GET request — show empty or pre-filled form
        initial_data = {}

        if not is_doctor:  # Patient
            profile = request.user.profile
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'phone_number': profile.phone_number,
                'email': request.user.email,
                'national_id': profile.national_id,
            }

        form = DonorForm(initial=initial_data)

        # Make personal fields readonly (NOT disabled!) for patients
        if not is_doctor:
            readonly_fields = ['first_name', 'last_name', 'national_id', 'phone_number', 'email']
            for field_name in readonly_fields:
                if field_name in form.fields:
                    form.fields[field_name].widget.attrs['readonly'] = 'readonly'

    return render(request, 'donors/donor_form.html', {
        'form': form,
        'is_doctor': is_doctor,
    })

from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from .models import Donation
from .forms import DonationForm
@doctor_required
def donation_create(request):
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donor = form.cleaned_data['donor']
            donation_date = form.cleaned_data['donation_date']
            
            # Check for recent donations within 56 days
            last_donation = Donation.objects.filter(
                donor=donor,
                donation_date__lt=donation_date
            ).order_by('-donation_date').first()
            
            if last_donation and (donation_date - last_donation.donation_date).days < 56:
                next_donation_date = last_donation.donation_date + timedelta(days=56)
                messages.error(
                    request,
                    f'יש להמתין 56 ימים בין תרומות! '
                    f'התרומה האחרונה הייתה ב-{last_donation.donation_date:%d/%m/%Y}. '
                    f'ניתן לתרום שוב החל מ-{next_donation_date:%d/%m/%Y}.'
                )
                return render(request, 'donors/donation_form.html', {'form': form})
            
            donation.is_approved = True
            donation.save()
            messages.success(request, 'תרומת הדם נרשמה בהצלחה!')
            return redirect('donor_list')
    else:
        form = DonationForm()
    
    return render(request, 'donors/donation_form.html', {'form': form})

@login_required
def request_blood(request):
    result = None
    is_patient = hasattr(request.user, 'profile') and request.user.profile.is_patient
    
    # Blood type compatibility dictionary
    BLOOD_TYPES_COMPATIBILITY = {
        'A+': 'A+, AB+',
        'A-': 'A+, A-, AB+, AB-',
        'B+': 'B+, AB+',
        'B-': 'B+, B-, AB+, AB-',
        'AB+': 'AB+',
        'AB-': 'AB+, AB-',
        'O+': 'O+, A+, B+, AB+',
        'O-': 'כל סוגי הדם'
    }
    
    # Get donor profile if user is a patient
    donor_profile = None
    if is_patient:
        try:
            donor_profile = Donor.objects.get(user=request.user)
            initial_data = {
                'patient_name': f"{donor_profile.first_name} {donor_profile.last_name}",
                'blood_type_needed': donor_profile.blood_type,
            }
        except Donor.DoesNotExist:
            initial_data = {}
    else:
        initial_data = {}

    if request.method == 'POST':
        form = BloodRequestForm(request.POST)
        if form.is_valid():
            blood_request = form.save(commit=False)
            blood_request.requested_by = request.user
            
            # For patients, enforce their own data
            if is_patient and donor_profile:
                blood_request.patient_name = f"{donor_profile.first_name} {donor_profile.last_name}"
                blood_request.blood_type_needed = donor_profile.blood_type
            
            # Emergency override (O- only)
            if blood_request.emergency:
                blood_request.blood_type_needed = 'O-'
                blood_request.priority = 'critical'
            
            blood_request.save()
            
            # Fulfillment logic
            if blood_request.priority == 'critical':
                result = fulfill_request(blood_request, emergency=True)
            else:
                result = fulfill_request(blood_request)
            
            if "fully fulfilled" in result[-1]:
                blood_request.fulfilled = True
                blood_request.save()
            
            # Show success message and stay on the same page
            messages.success(request, "בקשת הדם נשלחה בהצלחה!")
            
            # Option 1: Redirect back to the same page (refresh)
            # return redirect('request_blood')  # Make sure this URL name exists
            
            # Option 2: Stay on the same page with success message
            # Just continue to render the template below

    else:
        form = BloodRequestForm(initial=initial_data)
    
    return render(request, 'donors/request_form.html', {
        'form': form,
        'result': result,
        'is_patient': is_patient,
        'donor_profile': donor_profile,
        'blood_types': BLOOD_TYPES_COMPATIBILITY
    })

def fulfill_request(request, emergency=False):
    needed = request.units_needed
    matches = []
    blood_type = request.blood_type_needed
    
    # Emergency: only use O- blood
    if emergency:
        compatible_types = ['O-']
    else:
        compatible_types = COMPATIBLE.get(blood_type, [])
    
    # Get available donations (FIFO)
    donations = Donation.objects.filter(
        donor__blood_type__in=compatible_types,
        is_approved=True
    ).order_by('donation_date')
    
    for donation in donations:
        if needed <= 0:
            break
            
        if donation.volume_ml >= needed:
            matches.append(f"נלקחו {needed} מ\"ל מתרומה #{donation.id}")
            donation.volume_ml -= needed
            if donation.volume_ml == 0:
                donation.delete()
            else:
                donation.save()
            needed = 0
        else:
            matches.append(f"נלקחו {donation.volume_ml} מ\"ל מתרומה #{donation.id}")
            needed -= donation.volume_ml
            donation.delete()
    
    if needed == 0:
        matches.append("הבקשה מולאה בהצלחה! ✅")
    else:
        matches.append(f"אין מספיק מלאי! חסרים {needed} מ\"ל ❌")
    
    return matches

from django.db.models import Sum
from django.shortcuts import render
from datetime import date
from .models import Donation, BloodRequest, Donor
@doctor_required
def inventory_report(request):
    # Get inventory data grouped by blood type
    inventory_data = (
        Donation.objects
        .values('donor__blood_type')
        .annotate(total_volume=Sum('volume_ml'))
        .order_by('donor__blood_type')
    )
    
    # Calculate total volume and percentages
    total_ml = sum(item['total_volume'] for item in inventory_data if item['total_volume'])
    blood_types = dict(Donor.BLOOD_TYPES)
    
    # Build inventory dictionary with all blood types
    inventory = {}
    critical_stock = []
    
    for code, name in Donor.BLOOD_TYPES:
        # Find this blood type in the queryset
        blood_type_data = next(
            (item for item in inventory_data if item['donor__blood_type'] == code), 
            {'total_volume': 0}
        )
        
        units = blood_type_data['total_volume'] or 0
        percentage = (units / total_ml * 100) if total_ml > 0 else 0
        
        inventory[code] = {
            'units': units,
            'percentage': round(percentage, 2),
            'name': name
        }
        
        # Check for critical stock (less than 5 units)
        if units < 5:
            critical_stock.append(code)
    
    total_requests = BloodRequest.objects.filter(fulfilled=True).count()
    
    context = {
        'inventory': inventory,
        'total_volume': total_ml,
        'total_requests': total_requests,
        'today': date.today(),
        'critical_stock': critical_stock,
        'blood_types': blood_types
    }
    
    return render(request, 'donors/inventory_report.html', context)





from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum
from .models import Donor, Donation, BloodRequest
from django.utils import timezone
from django.http import JsonResponse

def emergency_request(request):
    if request.method == 'POST':
        units_needed = int(request.POST.get('units_needed', 0))
        
        if units_needed <= 0:
            messages.error(request, 'מספר היחידות חייב להיות גדול מ-0')
            return redirect('emergency_request')
        
        # Get all O- donors with their available blood amount
        o_negative_donors = Donor.objects.filter(blood_type='O-').annotate(
            total_donated=Sum('donations__volume_ml')
        ).order_by('total_donated')  # Prefer donors who donated less
        
        remaining_units = units_needed
        donation_messages = []
        
        for donor in o_negative_donors:
            if remaining_units <= 0:
                break
                
            # Calculate how much this donor can give (max 500ml per donation = ~1 unit)
            can_give = min(remaining_units, 1)  # 1 unit per donor for emergency
            
            if can_give > 0:
                # Create donation record
                donation = Donation.objects.create(
                    donor=donor,
                    donation_date=timezone.now().date(),
                    volume_ml=can_give * 450,  # Convert units to ml (450ml per unit)
                    notes=f"תרומת חירום אוטומטית - {can_give} יחידות",
                    is_approved=True
                )
                
                donation_messages.append(
                    f"נלקח דם מתורם {donor.first_name} {donor.last_name} "
                    f"(ת\"ז: {donor.national_id}) - {can_give} יחידות"
                )
                
                remaining_units -= can_give
        
        # Create blood request record
        blood_request = BloodRequest.objects.create(
            patient_name="חירום - מטופל אנונימי",
            blood_type_needed='O-',
            units_needed=units_needed,
            priority='critical',
            emergency=True,
            fulfilled=(remaining_units == 0)
        )
        
        # Prepare success message
        if remaining_units == 0:
            success_msg = (
                f"✅ בקשת החירום סופקה במלואה! {units_needed} יחידות O- נלקחו בהצלחה.\n"
                f"פירוט:\n" + "\n".join(donation_messages)
            )
            messages.success(request, success_msg)
        else:
            partial_msg = (
                f"⚠️ סופקו רק {units_needed - remaining_units} מתוך {units_needed} יחידות.\n"
                f"חסרות {remaining_units} יחידות.\n"
                f"פירוט התרומות:\n" + "\n".join(donation_messages)
            )
            messages.warning(request, partial_msg)
        
        return redirect('emergency_request')
    
    # Get statistics for the template
    
    o_negative_count = Donor.objects.filter(blood_type='O-').count()
    total_o_negative_ml = Donation.objects.filter(
        donor__blood_type='O-'
    ).aggregate(total=Sum('volume_ml'))['total'] or 0
    total_o_negative_units = total_o_negative_ml // 450
    
    # Get recent emergency requests
    recent_requests = BloodRequest.objects.filter(
        emergency=True
    ).order_by('-date_requested')[:10]
    
    context = {
        'o_negative_count': o_negative_count,
        'total_o_negative_units': total_o_negative_units,
        'available_units': o_negative_count,  # Each donor can give 1 unit
        'recent_requests': recent_requests
    }
    
    return render(request, 'donors/emergency_request.html', context)

def get_emergency_stats(request):
    """AJAX endpoint for real-time statistics"""
    o_negative_count = Donor.objects.filter(blood_type='O-').count()
    recent_donations = Donation.objects.filter(
        donor__blood_type='O-',
        donation_date__gte=timezone.now().date() - timezone.timedelta(days=30)
    ).count()
    
    return JsonResponse({
        'available_donors': o_negative_count,
        'recent_donations': recent_donations,
        'estimated_available_units': o_negative_count - recent_donations
    })




from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from .decorators import doctor_required, patient_required
from .forms import DoctorRegistrationForm, PatientRegistrationForm

from django.contrib import messages
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from .forms import DoctorRegistrationForm, PatientRegistrationForm
from django.contrib.auth.models import User

def register_doctor(request):
    if request.method == 'POST':
        form = DoctorRegistrationForm(request.POST)
        if form.is_valid():
            # Check if user already exists
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'שם משתמש זה כבר תפוס. אנא בחר שם משתמש אחר.')
            elif User.objects.filter(email=email).exists():
                form.add_error('email', 'אימייל זה כבר רשום במערכת.')
            else:
                try:
                    # Create the user
                    user = form.save()
                    
                    # CREATE OR UPDATE THE PROFILE WITH DOCTOR ROLE
                    profile, created = Profile.objects.get_or_create(
                        user=user,
                        defaults={'role': 'doctor'}
                    )
                    
                    # If profile already existed (shouldn't happen), update role
                    if not created:
                        profile.role = 'doctor'
                        profile.save()
                    
                    login(request, user)
                    messages.success(request, 'החשבון נוצר בהצלחה! ברוך הבא למערכת.')
                    return redirect('home')
                    
                except Exception as e:
                    # Handle any other unexpected errors
                    form.add_error(None, f'אירעה שגיאה ביצירת החשבון: {str(e)}')
        
        # If form is invalid or user exists, render form with errors
        return render(request, 'donors/register_doctor.html', {'form': form})
    
    else:
        form = DoctorRegistrationForm()
    
    return render(request, 'donors/register_doctor.html', {'form': form})

def register_patient(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            # Check if user already exists
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            national_id = form.cleaned_data.get('national_id')
            
            if User.objects.filter(username=username).exists():
                form.add_error('username', 'שם משתמש זה כבר תפוס. אנא בחר שם משתמש אחר.')
            elif User.objects.filter(email=email).exists():
                form.add_error('email', 'אימייל זה כבר רשום במערכת.')
            else:
                try:
                    user = form.save()
                    # Authenticate and login the user
                    user = authenticate(
                        username=form.cleaned_data['username'],
                        password=form.cleaned_data['password1']
                    )
                    if user is not None:
                        login(request, user)
                        messages.success(request, 'החשבון נוצר successfully! ברוך הבא למערכת.')
                        return redirect('patient_dashboard')
                    else:
                        form.add_error(None, 'לא ניתן להתחבר לאחר הרישום. אנא נסה להתחבר ידנית.')
                except Exception as e:
                    # Handle any other unexpected errors
                    form.add_error(None, f'אירעה שגיאה ביצירת החשבון: {str(e)}')
        # If form is invalid or user exists, render form with errors
        return render(request, 'donors/register_patient.html', {'form': form})
    
    else:
        form = PatientRegistrationForm()
    
    return render(request, 'donors/register_patient.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if hasattr(user, 'profile'):
                if user.profile.role == 'doctor':
                    return redirect('home')
                else:
                    return redirect('patient_dashboard')
            return redirect('home')
    return render(request, 'donors/login.html')

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import Donor, Donation, BloodRequest
from .decorators import patient_required


from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from .models import Donor, Donation, BloodRequest

@patient_required
def patient_dashboard(request):
    user = request.user
    context = {
        'user': user,
        'is_donor': False,
        'donor': None,
        'total_donations': 0,
        'last_donation': None,
        'next_donation_date': None,
        'days_until_next': 0,  # Default to 0
        'donation_progress_percentage': 0,  # ← Add this
        'blood_type': None,
        'user_requests': [],
        'total_requests': 0,
    }

    # Try to get the Donor profile linked to this user
    try:
        donor = Donor.objects.get(user=user)
        context['is_donor'] = True
        context['donor'] = donor
        context['blood_type'] = donor.blood_type

        # Get all donations by this donor
        donations = Donation.objects.filter(donor=donor, is_approved=True).order_by('-donation_date')
        context['total_donations'] = donations.count()

        if donations.exists():
            last_donation = donations.first()
            context['last_donation'] = last_donation

            # Calculate next allowed donation date (56 days rule)
            next_allowed = last_donation.donation_date + timedelta(days=56)
            context['next_donation_date'] = next_allowed

            # Days left until next donation
            today = timezone.now().date()
            if today < next_allowed:
                days_left = (next_allowed - today).days
                context['days_until_next'] = days_left
                # Calculate progress: how many days passed out of 56
                days_passed = 56 - days_left
                context['donation_progress_percentage'] = int((days_passed / 56) * 100)
            else:
                context['days_until_next'] = 0
                context['donation_progress_percentage'] = 100  # Ready to donate
        else:
            # No donations yet — can donate immediately
            context['days_until_next'] = 0
            context['donation_progress_percentage'] = 100

    except Donor.DoesNotExist:
        # User is not a donor → progress doesn't apply
        context['days_until_next'] = 0
        context['donation_progress_percentage'] = 0

    # Get blood requests made by this user
    user_requests = BloodRequest.objects.filter(requested_by=user).order_by('-date_requested')
    context['user_requests'] = user_requests
    context['total_requests'] = user_requests.count()

    return render(request, 'donors/patient_dashboard.html', context)

# UPDATE HOME FUNCTION:
def home(request):
    if request.user.is_authenticated:
        try:
            # Force reload the profile to ensure it's fresh
            profile = request.user.profile
            if profile.role == 'doctor':
                stats = {
                    'donors_count': Donor.objects.count(),
                    'active_donations': Donation.objects.filter(is_approved=True).count(),
                    'pending_requests': BloodRequest.objects.filter(fulfilled=False).count()
                }
                return render(request, 'donors/home.html', {'stats': stats})
            else:
                return redirect('patient_dashboard')
        except AttributeError:
            # Profile doesn't exist yet
            return render(request, 'donors/home.html')
    
    return render(request, 'donors/home.html')


@login_required
def profile_view(request):
    # Get the user's profile
    profile = request.user.profile
    
    # Calculate statistics based on user role
    if profile.role == 'doctor':
        stats = {
            'donors_count': Donor.objects.count(),
            'donations_count': Donation.objects.filter(is_approved=True).count(),
            'requests_count': BloodRequest.objects.count(),
            'emergencies_count': BloodRequest.objects.filter(priority='critical').count()
        }
    else:
        # For patients, get their specific requests and donations
        # Note: You'll need to adjust these queries based on your model relationships
        stats = {
            'blood_requests': BloodRequest.objects.filter(requested_by=request.user).count(),
            'donations_received': 0,  # You'll need to implement this based on your data model
            'approved_requests': BloodRequest.objects.filter(requested_by=request.user, fulfilled=True).count(),
            'emergencies_count': BloodRequest.objects.filter(requested_by=request.user, priority='critical').count()
        }
    
    context = {
        'user': request.user,
        'profile': profile,
        'stats': stats
    }
    
    return render(request, 'donors/profile.html', context)

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET", "POST"])  # Allow both GET and POST
def custom_logout(request):

    logout(request)
    return redirect('home')  # Or login, or wherever you want



# views/reports.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
import os

from .models import Donor, Donation, BloodRequest, Profile
from .utils.pdf_generator import generate_pdf, save_pdf_to_file
from .utils.email_service import send_email_with_attachment

@login_required
def generate_doctor_report(request):
    """Generate and email comprehensive report for doctors"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_doctor:
        return HttpResponse("Access denied. Doctor role required.", status=403)
    
    # Get all data
    donors = Donor.objects.all()
    donations = Donation.objects.all().select_related('donor')
    blood_requests = BloodRequest.objects.all().select_related('requested_by')
    
    context = {
        'doctor_name': request.user.get_full_name() or request.user.username,
        'report_date': timezone.now(),
        'donors': donors,
        'donations': donations,
        'blood_requests': blood_requests,
        'total_donors': donors.count(),
        'total_donations': donations.count(),
        'total_requests': blood_requests.count(),
    }
    
    # Generate PDF
    pdf_content = generate_pdf('donors/reports/doctor_report.html', context)
    
    if pdf_content:
        # Save PDF to file
        filename = f"doctor_report_{request.user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = save_pdf_to_file(pdf_content, filename)
        
        # Email the report
        subject = f"Blood Bank System - Comprehensive Report - {datetime.now().strftime('%Y-%m-%d')}"
        message = f"Dear Dr. {request.user.get_full_name() or request.user.username},\n\n"
        message += "Please find attached the comprehensive report of all records in the blood bank system.\n\n"
        message += "Best regards,\nBlood Bank System"
        
        try:
            send_email_with_attachment(
                subject, 
                message, 
                [request.user.email],
                filepath
            )
            email_sent = True
        except Exception as e:
            email_sent = False
        
        # Provide download link
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add success message
        from django.contrib import messages
        if email_sent:
            messages.success(request, "Report generated successfully and sent to your email!")
        else:
            messages.warning(request, "Report generated successfully but email could not be sent.")
        
        return response
    
    return HttpResponse("Failed to generate report.", status=500)

@login_required
def generate_patient_report(request):
    """Generate and email personal report for patients"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_patient:
        return HttpResponse("Access denied. Patient role required.", status=403)
    
    try:
        # Get patient's data
        donor = Donor.objects.get(user=request.user)
        donations = Donation.objects.filter(donor=donor)
        blood_requests = BloodRequest.objects.filter(requested_by=request.user)
        
        context = {
            'patient_name': f"{donor.first_name} {donor.last_name}",
            'report_date': timezone.now(),
            'donor': donor,
            'donations': donations,
            'blood_requests': blood_requests,
            'total_donations': donations.count(),
            'total_requests': blood_requests.count(),
        }
        
        # Generate PDF
        pdf_content = generate_pdf('donors/reports/patient_report.html', context)
        
        if pdf_content:
            # Save PDF to file
            filename = f"patient_report_{request.user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = save_pdf_to_file(pdf_content, filename)
            
            # Email the report
            recipient_email = donor.email or request.user.email
            subject = f"Your Blood Bank Records - {datetime.now().strftime('%Y-%m-%d')}"
            message = f"Dear {donor.first_name} {donor.last_name},\n\n"
            message += "Please find attached your personal blood bank records.\n\n"
            message += "Best regards,\nBlood Bank System"
            
            try:
                send_email_with_attachment(
                    subject, 
                    message, 
                    [recipient_email],
                    filepath
                )
                email_sent = True
            except Exception as e:
                email_sent = False
            
            # Provide download link
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Add success message
            from django.contrib import messages
            if email_sent:
                messages.success(request, "Report generated successfully and sent to your email!")
            else:
                messages.warning(request, "Report generated successfully but email could not be sent.")
            
            return response
        
        return HttpResponse("Failed to generate report.", status=500)
    
    except Donor.DoesNotExist:
        return HttpResponse("No donor record found for your account.", status=404)
    



# =====================
# NEW ENHANCEMENT FUNCTIONS (Add to your existing views.py)
# =====================

# 1. מיקום תורמים בקרבת מקום בחירום
@doctor_required
def emergency_donor_locator(request):
    """
    מציג תורמים קרובים כאשר אין מספיק מלאי לפי סוג דם
    """
    if request.method == 'POST':
        blood_type_needed = request.POST.get('blood_type')
        units_needed = int(request.POST.get('units_needed', 1))
        max_distance = int(request.POST.get('max_distance', 50))  # ק"מ
        
        # סוגי דם תואמים
        compatible_types = COMPATIBLE.get(blood_type_needed, [])
        
        available_donors = []
        for donor in Donor.objects.filter(blood_type__in=compatible_types):
            if donor.can_donate:
                # חישוב מרחק וזמינות
                distance = calculate_simple_distance(donor)
                if distance <= max_distance:
                    availability_score = calculate_availability_score(donor)
                    
                    available_donors.append({
                        'donor': donor,
                        'score': availability_score,
                        'distance_km': distance,
                        'last_donation': donor.last_donation_date,
                        'days_until_available': donor.days_until_next_donation,
                        'contact_info': f"{donor.phone_number}",
                        'can_donate_now': donor.days_until_next_donation == 0
                    })
        
        # מיון לפי זמינות (גבוה ביותר ראשון)
        available_donors.sort(key=lambda x: x['score'], reverse=True)
        
        context = {
            'blood_type_needed': blood_type_needed,
            'units_needed': units_needed,
            'max_distance': max_distance,
            'available_donors': available_donors,
            'total_found': len(available_donors),
            'compatible_types': [bt for bt in Donor.BLOOD_TYPES if bt[0] in compatible_types],
            'search_performed': True,
        }
        
        return render(request, 'donors/emergency_locator.html', context)
    
    # GET request - show search form
    return render(request, 'donors/emergency_locator.html', {
        'blood_types': Donor.BLOOD_TYPES,
        'search_performed': False
    })

def calculate_availability_score(donor):
    """מחשב ניקוד זמינות לתורם (ניקוד גבוה יותר = יותר זמין)"""
    score = 100
    
    # קנס על תרומה אחרונה
    if donor.last_donation_date:
        days_passed = (timezone.now().date() - donor.last_donation_date).days
        if days_passed < 56:
            score -= (56 - days_passed) * 2
    
    # בונוס על בריאות מעולה
    if donor.health_status == 'excellent':
        score += 20
    elif donor.health_status == 'good':
        score += 10
    
    # קנס על עישון/אלכוהול
    if donor.smoking_status != 'never':
        score -= 10
    if donor.alcohol_use != 'never':
        score -= 5
    
    return max(score, 0)

def calculate_simple_distance(donor):
    """חישוב מרחק פשוט - ניתן להחליף ב-GPS אמיתי later"""
    # מימוש לדוגמה - מחזיר מרחק אקראי בין 1-50 ק"מ
    return (hash(donor.national_id) % 50) + 1

# 2. מערכת התראות חירום המונית עם אימייל
@doctor_required
def mass_emergency_alert(request):
    """
    שולחת התראות חירום להמון תורמים באמצעות אימייל
    """
    if request.method == 'POST':
        blood_type = request.POST.get('blood_type')
        emergency_type = request.POST.get('emergency_type')
        custom_message = request.POST.get('custom_message', '')
        max_donors = int(request.POST.get('max_donors', 50))
        
        # הודעות חירום מוגדרות מראש
        emergency_messages = {
            'critical': {
                'subject': "🔴 בקשת חירום דחופה - תרומת דם נדרשת באופן מיידי",
                'message': """
שלום {donor_name},

בקשת חירום דחופה! נדרש דם מסוג {blood_type} באופן מיידי.

פרטים:
- סוג דם נדרש: {blood_type}
- רמת דחיפות: קריטית
- זמן מענה: מיידי

אנא פנה בהקדם האפשרי למרכז התרומות הקרוב אליך. תרומתך יכולה להציל חיים!

כתובת המרכז הקרוב: [כתובת המרכז]
טלפון: [מספר טלפון]

בברכה,
מערכת ניהול בנק הדם
                """
            },
            'mass_casualty': {
                'subject': "🆘 אירוע רב נפגעים - נדרשים תורמי דם בדחיפות",
                'message': """
שלום {donor_name},

אירוע רב נפגעים! נדרשים תורמי דם מסוג {blood_type} בדחיפות רבה.

פרטים:
- סוג דם נדרש: {blood_type}
- סוג אירוע: רב נפגעים
- דחיפות: גבוהה ביותר

חיי אדם בסכנה! אנא פנה מיידית למרכז התרומות הקרוב.

כתובת המרכז הקרוב: [כתובת המרכז]
טלפון: [מספר טלפון]

תודה על שיתוף הפעולה בהצלת חיים,
מערכת ניהול בנק הדם
                """
            },
            'surgery': {
                'subject': "💉 ניתוח דחוף - תרומת דם נדרשת לניתוח הצלה",
                'message': """
שלום {donor_name},

ניתוח דחוף! נדרש דם מסוג {blood_type} לניתוח הצלה.

פרטים:
- סוג דם נדרש: {blood_type}
- סוג צורך: ניתוח דחוף
- זמן מענה: בתוך 24 שעות

תרומתך יכולה לקבוע את ההבדל בין חיים למוות. אנא פנה למרכז התרומות.

כתובת המרכז הקרוב: [כתובת המרכז]
טלפון: [מספר טלפון]

בתודה ובברכה,
מערכת ניהול בנק הדם
                """
            }
        }
        
        # בחירת הודעה לפי סוג החירום
        message_template = emergency_messages.get(emergency_type, emergency_messages['critical'])
        
        # מציאת תורמים מתאימים
        compatible_donors = Donor.objects.filter(
            blood_type__in=COMPATIBLE.get(blood_type, [])
        )[:max_donors]
        
        alerted_donors = []
        failed_alerts = []
        
        for donor in compatible_donors:
            if donor.can_donate and donor.email:
                try:
                    # התאמת ההודעה לתורם
                    subject = message_template['subject']
                    message = message_template['message'].format(
                        donor_name=f"{donor.first_name} {donor.last_name}",
                        blood_type=blood_type
                    )
                    
                    # הוספת הודעה מותאמת אישית אם קיימת
                    if custom_message:
                        message += f"\n\nהערה נוספת: {custom_message}"
                    
                    # הוספת פרטים אישיים
                    message += f"\n\n---\nפרטים אישיים:"
                    message += f"\nתעודת זהות: {donor.national_id}"
                    message += f"\nסוג הדם שלך: {donor.blood_type}"
                    message += f"\nטלפון: {donor.phone_number}"
                    
                    # שליחת האימייל
                    from .utils.email_service import send_email_with_attachment
                    send_email_with_attachment(
                        subject=subject,
                        message=message,
                        recipient_list=[donor.email]
                    )
                    
                    alerted_donors.append({
                        'donor': donor,
                        'email': donor.email,
                        'blood_type': donor.blood_type,
                        'distance': calculate_simple_distance(donor),
                        'status': 'נשלח בהצלחה'
                    })
                    
                except Exception as e:
                    failed_alerts.append({
                        'donor': donor,
                        'email': donor.email,
                        'error': str(e),
                        'status': 'נכשל'
                    })
        
        # סטטיסטיקות שליחה
        total_sent = len(alerted_donors)
        total_failed = len(failed_alerts)
        
        context = {
            'alerted_count': total_sent,
            'failed_count': total_failed,
            'blood_type': blood_type,
            'emergency_type': emergency_type,
            'alerted_donors': alerted_donors,
            'failed_alerts': failed_alerts,
            'message_template': message_template,
            'custom_message': custom_message,
        }
        
        if total_sent > 0:
            messages.success(request, f"✅ התראות חירום נשלחו בהצלחה ל-{total_sent} תורמים")
        if total_failed > 0:
            messages.warning(request, f"⚠️ {total_failed} התראות נכשלו בשליחה")
        
        return render(request, 'donors/emergency_alert_results.html', context)
    
    # GET request - show the alert form
    return render(request, 'donors/mass_emergency_alert.html', {
        'blood_types': Donor.BLOOD_TYPES,
        'emergency_types': [
            ('critical', 'מצב קריטי - חירום מיידי'),
            ('mass_casualty', 'אירוע רב נפגעים'),
            ('surgery', 'ניתוח דחוף'),
        ]
    })

# 3. חיזוי מחסור בדם
@doctor_required
def blood_shortage_predictor(request):
    """
    חוזה מחסורים עתידיים בדם לפי נתוני שימוש
    """
    # ניתוח נתונים אחרונים (30 יום)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # בקשות אחרונות
    recent_requests = BloodRequest.objects.filter(
        date_requested__gte=thirty_days_ago
    )
    
    # תרומות אחרונות
    recent_donations = Donation.objects.filter(
        donation_date__gte=thirty_days_ago
    )
    
    # חישוב מגמות לפי סוג דם
    shortage_predictions = []
    for blood_type, blood_name in Donor.BLOOD_TYPES:
        # בקשות עבור סוג דם זה
        type_requests = recent_requests.filter(blood_type_needed=blood_type)
        total_requests = type_requests.count()
        units_requested = type_requests.aggregate(total=Sum('units_needed'))['total'] or 0
        
        # תרומות של סוג דם זה
        type_donations = recent_donations.filter(donor__blood_type=blood_type)
        total_donations = type_donations.count()
        units_donated = type_donations.aggregate(total=Sum('volume_ml'))['total'] or 0
        units_donated = units_donated // 450  # המרה ליחידות
        
        # מלאי נוכחי
        current_inventory = Donation.objects.filter(
            donor__blood_type=blood_type,
            is_approved=True
        ).aggregate(total=Sum('volume_ml'))['total'] or 0
        current_units = current_inventory // 450
        
        # חיזוי מחסור
        daily_usage = units_requested / 30 if units_requested > 0 else 0.1
        days_until_shortage = current_units / daily_usage if daily_usage > 0 else 999
        
        # דירוג סיכון
        if days_until_shortage < 7:
            risk_level = 'high'
            risk_text = 'סיכון גבוה'
        elif days_until_shortage < 14:
            risk_level = 'medium'
            risk_text = 'סיכון בינוני'
        else:
            risk_level = 'low'
            risk_text = 'סיכון נמוך'
        
        shortage_predictions.append({
            'blood_type': blood_type,
            'blood_name': blood_name,
            'current_units': current_units,
            'daily_usage': round(daily_usage, 1),
            'days_until_shortage': round(days_until_shortage, 1),
            'risk_level': risk_level,
            'risk_text': risk_text,
            'total_requests': total_requests,
            'total_donations': total_donations,
        })
    
    # מיון לפי סיכון (גבוה ראשון)
    shortage_predictions.sort(key=lambda x: x['days_until_shortage'])
    
    context = {
        'predictions': shortage_predictions,
        'analysis_date': timezone.now(),
        'period_days': 30,
    }
    
    return render(request, 'donors/shortage_predictor.html', context)

# 4. לוח זמינות תורמים
@doctor_required
def donor_availability_calendar(request):
    """
    מציג מתי תורמים יכולים לתרום שוב לפי כלל 56 הימים
    """
    # תורמים שתרמו לאחרונה
    recent_donors = Donor.objects.filter(
        donations__isnull=False
    ).annotate(
        last_donation_date=Max('donations__donation_date'),
        total_donations=Count('donations')
    ).exclude(last_donation_date__isnull=True).order_by('-last_donation_date')
    
    availability_data = []
    for donor in recent_donors:
        next_donation_date = donor.last_donation_date + timedelta(days=56)
        days_until_available = (next_donation_date - timezone.now().date()).days
        can_donate_now = days_until_available <= 0
        
        availability_data.append({
            'donor': donor,
            'last_donation_date': donor.last_donation_date,
            'next_donation_date': next_donation_date,
            'days_until_available': days_until_available,
            'can_donate_now': can_donate_now,
            'total_donations': donor.total_donations,
        })
    
    # גם תורמים שמעולם לא תרמו
    new_donors = Donor.objects.filter(donations__isnull=True)
    
    context = {
        'available_donors': [d for d in availability_data if d['can_donate_now']],
        'soon_available': [d for d in availability_data if not d['can_donate_now'] and d['days_until_available'] <= 7],
        'future_available': [d for d in availability_data if not d['can_donate_now'] and d['days_until_available'] > 7],
        'new_donors': new_donors,
        'today': timezone.now().date(),
    }
    
    return render(request, 'donors/availability_calendar.html', context)

# 5. התאמת תורמים חכמה לבקשות
@doctor_required
def smart_donor_matching(request, request_id=None):
    """
    מוצא את התורמים האופטימליים עבור בקשה ספציפית
    """
    if request_id:
        # התאמה לבקשה ספציפית
        blood_request = BloodRequest.objects.get(id=request_id)
        blood_type = blood_request.blood_type_needed
        units_needed = blood_request.units_needed
    else:
        # התאמה כללית
        blood_type = request.GET.get('blood_type', 'O+')
        units_needed = int(request.GET.get('units_needed', 1))
        blood_request = None
    
    compatible_types = COMPATIBLE.get(blood_type, [])
    
    # מציאת התורמים המתאימים ביותר
    matched_donors = []
    for donor in Donor.objects.filter(blood_type__in=compatible_types):
        if donor.can_donate:
            match_score = calculate_match_score(donor, blood_type, units_needed)
            
            matched_donors.append({
                'donor': donor,
                'match_score': match_score,
                'distance': calculate_simple_distance(donor),
                'last_donation': donor.last_donation_date,
                'can_donate_now': donor.days_until_next_donation == 0,
                'health_status': donor.health_status,
                'contact_info': donor.phone_number,
            })
    
    # מיון לפי דירוג ההתאמה (גבוה ביותר ראשון)
    matched_donors.sort(key=lambda x: x['match_score'], reverse=True)
    
    context = {
        'blood_request': blood_request,
        'blood_type': blood_type,
        'units_needed': units_needed,
        'matched_donors': matched_donors,
        'compatible_types': compatible_types,
        'total_matches': len(matched_donors),
    }
    
    return render(request, 'donors/smart_matching.html', context)

def calculate_match_score(donor, needed_blood_type, units_needed):
    """
    מחשב דירוג התאמה בין תורם לבקשה
    """
    score = 100
    
    # התאמת סוג דם (מדויק יותר = ניקוד גבוה יותר)
    if donor.blood_type == needed_blood_type:
        score += 30
    elif needed_blood_type in ['O-', 'O+'] and donor.blood_type == needed_blood_type:
        score += 50
    
    # זמינות מיידית
    if donor.days_until_next_donation == 0:
        score += 40
    
    # מצב בריאותי
    if donor.health_status == 'excellent':
        score += 25
    elif donor.health_status == 'good':
        score += 15
    
    # מרחק (קרוב יותר = טוב יותר)
    distance = calculate_simple_distance(donor)
    if distance <= 10:
        score += 20
    elif distance <= 25:
        score += 10
    
    # ניסיון תרומה (יותר ניסיון = טוב יותר)
    total_donations = donor.donations.count()
    if total_donations > 5:
        score += 15
    elif total_donations > 0:
        score += 5
    
    return score

# AJAX endpoint for real-time availability check
def check_donor_availability(request):
    """בדיקת זמינות תורמים בזמן אמת"""
    blood_type = request.GET.get('blood_type')
    
    available_count = Donor.objects.filter(
        blood_type__in=COMPATIBLE.get(blood_type, []),
        donations__is_approved=True
    ).distinct().count()
    
    immediate_available = Donor.objects.filter(
        blood_type__in=COMPATIBLE.get(blood_type, []),
        donations__is_approved=True
    ).annotate(
        last_donation=Max('donations__donation_date')
    ).filter(
        Q(last_donation__isnull=True) | 
        Q(last_donation__lte=timezone.now().date() - timedelta(days=56))
    ).count()
    
    return JsonResponse({
        'available_donors': available_count,
        'immediate_available': immediate_available,
        'blood_type': blood_type
    })

# פונקציית חירום מהירה - לשליחה מהירה ללא טופס
@doctor_required
def quick_emergency_alert(request, blood_type, emergency_type='critical'):
    """
    שליחת התראות חירום מהירות דרך URL
    """
    # בדיקה אם סוג הדם תקין
    valid_blood_types = [bt[0] for bt in Donor.BLOOD_TYPES]
    if blood_type not in valid_blood_types:
        messages.error(request, f"סוג דם {blood_type} אינו תקין")
        return redirect('mass_emergency_alert')
    
    # מציאת תורמים מתאימים
    compatible_donors = Donor.objects.filter(
        blood_type__in=COMPATIBLE.get(blood_type, [])
    )[:20]  # הגבלה ל-20 תורמים לשליחה מהירה
    
    alerted_donors = []
    for donor in compatible_donors:
        if donor.can_donate and donor.email:
            try:
                subject = f"🔴 חירום - נדרש דם מסוג {blood_type}"
                message = f"""
שלום {donor.first_name} {donor.last_name},

בקשת חירום דחופה! נדרש דם מסוג {blood_type} באופן מיידי.

אנא פנה בהקדם למרכז התרומות הקרוב אליך.

פרטיך:
- סוג דם: {donor.blood_type}
- טלפון: {donor.phone_number}

כתובת המרכז הקרוב: [כתובת המרכז]
טלפון: [מספר טלפון]

בברכה,
מערכת ניהול בנק הדם
                """
                
                from .utils.email_service import send_email_with_attachment
                send_email_with_attachment(
                    subject=subject,
                    message=message,
                    recipient_list=[donor.email]
                )
                
                alerted_donors.append(donor)
                
            except Exception as e:
                print(f"שגיאה בשליחה ל-{donor.email}: {e}")
    
    messages.success(request, f"התראות חירום נשלחו ל-{len(alerted_donors)} תורמים מסוג {blood_type}")
    return redirect('mass_emergency_alert')

# בדיקת תפוסת אימיילים לפני שליחה
@doctor_required
def check_email_capacity(request):
    """
    בודק כמה תורמים עם אימייל זמינים לפני שליחה המונית
    """
    blood_type = request.GET.get('blood_type', 'O+')
    
    # תורמים עם אימייל שזמינים לתרומה
    available_with_email = Donor.objects.filter(
        blood_type__in=COMPATIBLE.get(blood_type, []),
        email__isnull=False,
        donations__is_approved=True
    ).distinct().count()
    
    # תורמים זמינים מיידית עם אימייל
    immediate_with_email = Donor.objects.filter(
        blood_type__in=COMPATIBLE.get(blood_type, []),
        email__isnull=False,
        donations__is_approved=True
    ).annotate(
        last_donation=Max('donations__donation_date')
    ).filter(
        Q(last_donation__isnull=True) | 
        Q(last_donation__lte=timezone.now().date() - timedelta(days=56))
    ).count()
    
    return JsonResponse({
        'available_with_email': available_with_email,
        'immediate_with_email': immediate_with_email,
        'blood_type': blood_type,
        'compatible_types': COMPATIBLE.get(blood_type, [])
    })

   