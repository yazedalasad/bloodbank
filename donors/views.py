from django.shortcuts import render, redirect
from django.db.models import Sum,Max
from .models import Donor, Donation, BloodRequest
from .forms import DonorForm, DonationForm, BloodRequestForm

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
    
    if blood_type_filter:
        donors = donors.filter(blood_type=blood_type_filter)
    
    # Calculate blood type distribution
    total_donors = donors.count()
    blood_type_stats = []
    
    # Get counts for each blood type
    blood_type_counts = donors.values('blood_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate percentages
    for item in blood_type_counts:
        percentage = (item['count'] / total_donors * 100) if total_donors > 0 else 0
        blood_type_stats.append({
            'blood_type': item['blood_type'],
            'count': item['count'],
            'percentage': round(percentage, 1)
        })
    
    # Prepare donor stats
    donor_stats = {
        'total': total_donors,
        'o_negative': donors.filter(blood_type='O-').count(),
        'blood_type_distribution': blood_type_stats
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

def donor_create(request):
    if request.method == 'POST':
        form = DonorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('donor_list')
    else:
        form = DonorForm()
    return render(request, 'donors/donor_form.html', {'form': form})

from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from .models import Donation
from .forms import DonationForm

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

def request_blood(request):
    result = None
    if request.method == 'POST':
        form = BloodRequestForm(request.POST)
        if form.is_valid():
            blood_request = form.save(commit=False)
            
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
    else:
        form = BloodRequestForm()
    
    return render(request, 'donors/request_form.html', {
        'form': form,
        'result': result
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

def home(request):
    stats = {
        'donors_count': Donor.objects.count(),
        'active_donations': Donation.objects.filter(is_approved=True).count(),
        'pending_requests': BloodRequest.objects.filter(fulfilled=False).count()
    }
    return render(request, 'donors/home.html', {'stats': stats})