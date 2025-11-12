from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F
from decimal import Decimal

from storefront.models import Product, Order, OrderItem
from users.models import Customer
from .decorators import staff_required


def admin_login(request):
    """Admin login page"""
    # Redirect if already authenticated and is staff
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_staff:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('admin_panel:dashboard')
            else:
                messages.error(request, 'You do not have permission to access the admin panel.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'admin_panel/admin_login.html')


@staff_required
def admin_logout(request):
    """Admin logout - logs out and redirects to admin login"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('admin_panel:admin_login')


@staff_required
def dashboard(request):
    """Admin dashboard with key metrics and recent activity"""
    
    # Calculate metrics
    total_revenue = Order.objects.filter(status='delivered').aggregate(
        total=Sum('total_price')
    )['total'] or Decimal('0.00')
    
    total_orders = Order.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()
    
    # Get recent orders
    recent_orders = Order.objects.select_related('customer__user').order_by('-created_at')[:5]
    
    # Get low stock products
    low_stock_products = Product.objects.filter(
        stock__lte=F('reorder_threshold')
    ).order_by('stock')[:5]
    
    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'total_products': total_products,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


# Protected placeholder views for future implementation
@staff_required
def product_management(request):
    """Product management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Product Management',
        'page_description': 'Manage products, add new items, edit existing products'
    })


@staff_required
def category_management(request):
    """Category management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Category Management',
        'page_description': 'Manage product categories'
    })


@staff_required
def inventory_management(request):
    """Inventory management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Inventory Management',
        'page_description': 'Track and manage product stock levels'
    })


@staff_required
def pricing_management(request):
    """Pricing management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Pricing Management',
        'page_description': 'Manage product pricing and discounts'
    })


@staff_required
def customer_records(request):
    """Customer records view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Customer Records',
        'page_description': 'View and manage customer information'
    })


@staff_required
def order_management(request):
    """Order management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Order Management',
        'page_description': 'View and process customer orders'
    })


@staff_required
def review_management(request):
    """Review management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Review Management',
        'page_description': 'Moderate and manage product reviews'
    })


@staff_required
def promotion_management(request):
    """Promotion management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Promotion Management',
        'page_description': 'Create and manage promotional campaigns'
    })


@staff_required
def chat_support(request):
    """Chat support view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Chat Support',
        'page_description': 'Respond to customer support inquiries'
    })


@staff_required
def import_export(request):
    """Data import/export view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Data Import/Export',
        'page_description': 'Import and export data in various formats'
    })


@staff_required
def recommendation_management(request):
    """Recommendation management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Recommendation Management',
        'page_description': 'Configure and monitor ML-based product recommendations'
    })


@staff_required
def preferred_category_analysis(request):
    """Preferred category analysis view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Preferred Category Analysis',
        'page_description': 'Analyze customer category preferences using ML'
    })


@staff_required
def audit_log(request):
    """Audit log view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Audit Log',
        'page_description': 'View system audit logs and admin activities'
    })


@staff_required
def admin_user_management(request):
    """Admin user management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Admin User Management',
        'page_description': 'Manage admin users and permissions'
    })

