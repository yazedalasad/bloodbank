from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from functools import wraps

from django.contrib import messages

def doctor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            if request.user.profile.role == 'doctor':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "גישה זו מוגבלת לרופאים בלבד.")
                return redirect('home')
        except (AttributeError, Profile.DoesNotExist):
            messages.error(request, "פרופיל לא קיים או אין הרשאה.")
            return redirect('home')
    
    return _wrapped_view


def patient_required(view_func):
    """
    Decorator that checks if the user has a patient profile.
    Redirects to appropriate page if not authenticated or not a patient.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check if user has a profile and is a patient
        if hasattr(request.user, 'profile') and request.user.profile.role == 'patient':
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("You don't have permission to access this page.")
    
    return _wrapped_view