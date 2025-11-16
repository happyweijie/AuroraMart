from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User, Customer
from .forms import CustomerRegistrationForm, CustomerLoginForm, PasswordChangeForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from mlservices.predict_preferred_category import get_preferred_category

# Create your views here.
def user_login(request):
    if request.user.is_authenticated:
        return redirect('storefront:home')
    
    if request.method == 'POST':
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                next_url = request.GET.get('next', 'storefront:home')
                return redirect(next_url)
    else:
        form = CustomerLoginForm()
    
    return render(request, 'users/login.html', {
        'form': form
        })


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('storefront:home')

def register(request):
    if request.user.is_authenticated:
        return redirect('storefront:home')
    
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # populate preferred category using ML model
            customer = user.customer_profile

            # set up customer's preferred category prediction
            preferred_category, preferred_category_fk = get_preferred_category(customer)
            print(f"Predicted preferred category: {preferred_category}")
            
            # set preferred category and fk
            customer.preferred_category = preferred_category
            customer.preferred_category_fk = preferred_category_fk
            customer.save()
            
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to AuroraMart.')
            return redirect('storefront:home')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'users/register.html', {
        'form': form
        })


@login_required
def profile(request):
    """Display user profile and handle password change"""
    user = request.user
    customer = None
    
    # Get customer profile if exists
    if hasattr(user, 'customer_profile'):
        customer = user.customer_profile
    
    password_form = None
    password_change_success = False
    
    # Handle password change
    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, user)  # Keep user logged in after password change
            messages.success(request, 'Your password has been changed successfully.')
            password_change_success = True
            password_form = None  # Reset form after successful change
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        password_form = PasswordChangeForm(user)
    
    context = {
        'user': user,
        'customer': customer,
        'password_form': password_form,
        'password_change_success': password_change_success,
    }
    
    return render(request, 'users/profile.html', context)

