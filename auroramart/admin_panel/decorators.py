from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def staff_required(view_func):
    """
    Decorator that checks if the user is authenticated and is a staff member.
    Redirects to admin login page if not authenticated or not staff.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in to access the admin panel.')
            return redirect('admin_panel:admin_login')
        
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to access the admin panel.')
            return redirect('storefront:home')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
