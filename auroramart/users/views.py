from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User, Customer
from .forms import CustomerRegistrationForm, CustomerLoginForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

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
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to AuroraMart.')
            return redirect('storefront:home')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'users/register.html', {
        'form': form
        })

