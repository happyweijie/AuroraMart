from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from decimal import Decimal

from storefront.models import Product, Order, OrderItem
from users.models import Customer


# @login_required  # Temporarily disabled for testing
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

