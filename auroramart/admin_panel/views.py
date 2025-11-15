from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, Q, Avg, Count, Case, When, IntegerField
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from storefront.models import Product, Order, OrderItem, Category, Review
from users.models import Customer
from admin_panel.models import RecommendationPlacement, AnalyticsMetric, AuditLog
from .decorators import staff_required
from .forms import ProductForm, CategoryForm, BulkInventoryUpdateForm, CustomerForm, OrderStatusUpdateForm


def admin_login(request):
    """Admin login page"""
    # Redirect if already authenticated and is staff
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_panel:dashboard')
    
    # Clear any existing messages from other parts of the app (consume all messages)
    list(messages.get_messages(request))
    
    login_messages = []
    
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
        
        # Only show messages that were just created (login-related)
        login_messages = list(messages.get_messages(request))
    
    return render(request, 'admin_panel/admin_login.html', {
        'login_messages': login_messages
    })


@staff_required
def admin_logout(request):
    """Admin logout - logs out and redirects to admin login"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('admin_panel:admin_login')


@staff_required
def dashboard(request):
    """Admin dashboard with key metrics and recent activity"""
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    # Calculate total revenue (delivered orders only)
    total_revenue = Order.objects.filter(status='delivered').aggregate(
        total=Sum('total_price')
    )['total'] or Decimal('0.00')
    
    # Orders today
    orders_today = Order.objects.filter(created_at__gte=today_start).count()
    
    # Orders this week
    orders_this_week = Order.objects.filter(created_at__gte=week_start).count()
    
    # Average Order Value (AOV)
    aov_result = Order.objects.filter(status='delivered').aggregate(
        avg=Avg('total_price')
    )
    aov = aov_result['avg'] or Decimal('0.00')
    
    # Attach rate (% orders with >1 item)
    total_orders_with_items = Order.objects.annotate(
        item_count=Count('items')
    ).filter(item_count__gt=1).count()
    total_orders_count = Order.objects.count()
    attach_rate = (total_orders_with_items / total_orders_count * 100) if total_orders_count > 0 else Decimal('0.00')
    
    # Low stock count (products below reorder threshold)
    low_stock_count = Product.objects.filter(
        stock__lte=F('reorder_threshold'),
        archived=False
    ).count()
    
    # Total counts
    total_orders = Order.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.filter(archived=False).count()
    
    # Save metrics to AnalyticsMetric
    AnalyticsMetric.objects.create(metric='aov', value=aov)
    AnalyticsMetric.objects.create(metric='attach_rate', value=attach_rate)
    AnalyticsMetric.objects.create(metric='low_stock_count', value=low_stock_count)
    
    # Get recent orders
    recent_orders = Order.objects.select_related('customer__user').order_by('-created_at')[:5]
    
    # Get low stock products
    low_stock_products = Product.objects.filter(
        stock__lte=F('reorder_threshold'),
        archived=False
    ).order_by('stock')[:5]
    
    context = {
        'total_revenue': total_revenue,
        'orders_today': orders_today,
        'orders_this_week': orders_this_week,
        'aov': aov,
        'attach_rate': attach_rate,
        'low_stock_count': low_stock_count,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'total_products': total_products,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


# ============ PRODUCT MANAGEMENT ============

@staff_required
def product_list(request):
    """List all products with search and filters"""
    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    products = Product.objects.select_related('category').all()
    
    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Apply category filter
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Apply status filter
    if status_filter == 'active':
        products = products.filter(is_active=True, archived=False)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False, archived=False)
    elif status_filter == 'archived':
        products = products.filter(archived=True)
    
    # Order by name
    products = products.order_by('name')
    
    # Pagination
    paginator = Paginator(products, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all categories for filter dropdown
    categories = Category.objects.all().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_filter,
        'selected_status': status_filter,
    }
    
    return render(request, 'admin_panel/product_list.html', context)


@staff_required
def product_create(request):
    """Create a new product"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('admin_panel:product_list')
    else:
        form = ProductForm()
    
    return render(request, 'admin_panel/product_form.html', {
        'form': form,
        'form_title': 'Create New Product',
        'submit_label': 'Create Product'
    })


@staff_required
def product_update(request, sku):
    """Update an existing product"""
    product = get_object_or_404(Product, sku=sku)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('admin_panel:product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'admin_panel/product_form.html', {
        'form': form,
        'product': product,
        'form_title': f'Edit Product: {product.name}',
        'submit_label': 'Update Product'
    })


@staff_required
def product_delete(request, sku):
    """Delete or archive a product"""
    product = get_object_or_404(Product, sku=sku)
    
    if request.method == 'POST':
        product_name = product.name
        # Archive instead of delete to preserve order history
        product.archived = True
        product.is_active = False
        product.save()
        messages.success(request, f'Product "{product_name}" has been archived.')
        return redirect('admin_panel:product_list')
    
    return render(request, 'admin_panel/product_confirm_delete.html', {
        'product': product
    })


# Alias for backward compatibility
@staff_required
def product_management(request):
    """Redirect to product list"""
    return redirect('admin_panel:product_list')


# ============ CATEGORY MANAGEMENT ============

@staff_required
def category_list(request):
    """List all categories"""
    categories = Category.objects.select_related('parent').all().order_by('name')
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'admin_panel/category_list.html', context)


@staff_required
def category_create(request):
    """Create a new category"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully!')
            return redirect('admin_panel:category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'admin_panel/category_form.html', {
        'form': form,
        'form_title': 'Create New Category',
        'submit_label': 'Create Category'
    })


@staff_required
def category_update(request, category_id):
    """Update an existing category"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('admin_panel:category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'admin_panel/category_form.html', {
        'form': form,
        'category': category,
        'form_title': f'Edit Category: {category.name}',
        'submit_label': 'Update Category'
    })


# Alias for backward compatibility
@staff_required
def category_management(request):
    """Redirect to category list"""
    return redirect('admin_panel:category_list')


# ============ INVENTORY MANAGEMENT ============

@staff_required
def inventory_management(request):
    """Inventory management with bulk updates"""
    search_query = request.GET.get('q', '').strip()
    filter_type = request.GET.get('filter', '')
    
    products = Product.objects.select_related('category').filter(archived=False)
    
    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Apply filter
    if filter_type == 'low_stock':
        products = products.filter(stock__lte=F('reorder_threshold'))
    elif filter_type == 'out_of_stock':
        products = products.filter(stock=0)
    
    # Order by stock (lowest first) then name
    products = products.order_by('stock', 'name')
    
    # Handle bulk update
    if request.method == 'POST' and 'bulk_update' in request.POST:
        form = BulkInventoryUpdateForm(request.POST)
        if form.is_valid():
            selected_products = form.cleaned_data['products']
            adjustment = form.cleaned_data['stock_adjustment']
            
            updated_count = 0
            for product in selected_products:
                new_stock = product.stock + adjustment
                if new_stock >= 0:
                    product.stock = new_stock
                    product.save()
                    updated_count += 1
                else:
                    messages.warning(request, f'{product.name}: Cannot set stock below 0.')
            
            if updated_count > 0:
                messages.success(request, f'Updated stock for {updated_count} product(s).')
            return redirect('admin_panel:inventory')
    else:
        form = BulkInventoryUpdateForm()
        # Pre-populate with products matching current filters
        if filter_type == 'low_stock':
            form.fields['products'].queryset = Product.objects.filter(
                archived=False, stock__lte=F('reorder_threshold')
            )
    
    # Pagination
    paginator = Paginator(products, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'search_query': search_query,
        'selected_filter': filter_type,
    }
    
    return render(request, 'admin_panel/inventory.html', context)


@staff_required
def pricing_management(request):
    """Pricing management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Pricing Management',
        'page_description': 'Manage product pricing and discounts'
    })


# ============ CUSTOMER MANAGEMENT ============

@staff_required
def customer_list(request):
    """List all customers with search"""
    search_query = request.GET.get('q', '').strip()
    
    customers = Customer.objects.select_related('user').all()
    
    # Apply search filter
    if search_query:
        customers = customers.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Order by username
    customers = customers.order_by('user__username')
    
    # Pagination
    paginator = Paginator(customers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'admin_panel/customer_list.html', context)


@staff_required
def customer_update(request, customer_id):
    """Update customer demographics"""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.user.username}" updated successfully!')
            return redirect('admin_panel:customer_list')
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'admin_panel/customer_form.html', {
        'form': form,
        'customer': customer,
        'form_title': f'Edit Customer: {customer.user.username}',
        'submit_label': 'Update Customer'
    })


# Alias for backward compatibility
@staff_required
def customer_records(request):
    """Redirect to customer list"""
    return redirect('admin_panel:customer_list')


# ============ ORDER MANAGEMENT ============

@staff_required
def admin_order_list(request):
    """List all orders with status filters"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '').strip()
    
    orders = Order.objects.select_related('customer__user').all()
    
    # Apply status filter
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Apply search filter
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(customer__user__username__icontains=search_query) |
            Q(customer__user__email__icontains=search_query)
        )
    
    # Order by most recent first
    orders = orders.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'selected_status': status_filter,
        'search_query': search_query,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'admin_panel/admin_order_list.html', context)


@staff_required
def admin_order_detail(request, order_id):
    """View and update order details"""
    order = get_object_or_404(Order.objects.select_related('customer__user'), id=order_id)
    order_items = order.items.select_related('product').all()
    
    if request.method == 'POST':
        form = OrderStatusUpdateForm(request.POST)
        if form.is_valid():
            old_status = order.status
            order.status = form.cleaned_data['status']
            order.save()
            messages.success(request, f'Order #{order.id} status updated from {old_status} to {order.status}.')
            return redirect('admin_panel:admin_order_detail', order_id=order_id)
    else:
        form = OrderStatusUpdateForm(initial={'status': order.status})
    
    context = {
        'order': order,
        'order_items': order_items,
        'form': form,
    }
    
    return render(request, 'admin_panel/admin_order_detail.html', context)


# Alias for backward compatibility
@staff_required
def order_management(request):
    """Redirect to order list"""
    return redirect('admin_panel:admin_order_list')


def _recalculate_product_rating(product):
    """Recalculate and update product rating based on approved reviews"""
    approved_reviews = Review.objects.filter(product=product, is_approved=True)
    total_reviews = approved_reviews.count()
    
    if total_reviews > 0:
        average_rating = sum(review.rating for review in approved_reviews) / total_reviews
        product.rating = round(Decimal(str(average_rating)), 2)
    else:
        product.rating = Decimal('0.0')
    product.save()


@staff_required
def review_management(request):
    """Review moderation and management view"""
    status_filter = request.GET.get('status', 'pending')  # pending, approved, all
    search_query = request.GET.get('q', '').strip()
    
    # Base queryset
    reviews = Review.objects.select_related('product', 'product__category', 'customer', 'customer__user').all()
    
    # Apply status filter
    if status_filter == 'pending':
        reviews = reviews.filter(is_approved=False)
    elif status_filter == 'approved':
        reviews = reviews.filter(is_approved=True)
    # 'all' shows everything
    
    # Apply search filter
    if search_query:
        reviews = reviews.filter(
            Q(product__name__icontains=search_query) |
            Q(product__sku__icontains=search_query) |
            Q(customer__user__username__icontains=search_query) |
            Q(customer__user__email__icontains=search_query) |
            Q(comment__icontains=search_query) |
            Q(title__icontains=search_query)
        )
    
    # Handle bulk actions
    if request.method == 'POST':
        action = request.POST.get('action', '')
        review_ids = request.POST.getlist('review_ids')
        
        if action == 'approve' and review_ids:
            # Get products that need rating recalculation
            products_to_update = set()
            updated_count = 0
            
            for review_id in review_ids:
                try:
                    review = Review.objects.get(id=review_id)
                    if not review.is_approved:
                        review.is_approved = True
                        review.save()
                        products_to_update.add(review.product)
                        updated_count += 1
                        
                        # Create audit log
                        AuditLog.objects.create(
                            actor=request.user,
                            action='update',
                            entity_type='Review',
                            entity_id=str(review.id),
                            summary=f'Approved review for {review.product.name}'
                        )
                except Review.DoesNotExist:
                    pass
            
            # Recalculate ratings for affected products
            for product in products_to_update:
                _recalculate_product_rating(product)
            
            messages.success(request, f'{updated_count} review(s) approved successfully.')
            return redirect('admin_panel:reviews')
        
        elif action == 'reject' and review_ids:
            # For reject, we delete the review
            products_to_update = set()
            deleted_count = 0
            
            for review_id in review_ids:
                try:
                    review = Review.objects.get(id=review_id)
                    product = review.product
                    product_name = product.name
                    products_to_update.add(product)
                    
                    # Create audit log before deleting
                    AuditLog.objects.create(
                        actor=request.user,
                        action='delete',
                        entity_type='Review',
                        entity_id=str(review.id),
                        summary=f'Rejected review for {product_name}'
                    )
                    review.delete()
                    deleted_count += 1
                except Review.DoesNotExist:
                    pass
            
            # Recalculate ratings for affected products
            for product in products_to_update:
                _recalculate_product_rating(product)
            
            messages.success(request, f'{deleted_count} review(s) rejected and deleted.')
            return redirect('admin_panel:reviews')
    
    # Order by most recent first
    reviews = reviews.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(reviews, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Counts for status badges
    pending_count = Review.objects.filter(is_approved=False).count()
    approved_count = Review.objects.filter(is_approved=True).count()
    total_count = Review.objects.count()
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'total_count': total_count,
    }
    
    return render(request, 'admin_panel/review_moderation.html', context)


@staff_required
def review_approve(request, review_id):
    """Approve a single review"""
    review = get_object_or_404(Review, id=review_id)
    
    if not review.is_approved:
        review.is_approved = True
        review.save()
        
        # Recalculate product rating
        _recalculate_product_rating(review.product)
        
        # Create audit log
        AuditLog.objects.create(
            actor=request.user,
            action='update',
            entity_type='Review',
            entity_id=str(review.id),
            summary=f'Approved review for {review.product.name}'
        )
        
        messages.success(request, f'Review for {review.product.name} has been approved.')
    else:
        messages.info(request, f'Review for {review.product.name} is already approved.')
    
    return redirect('admin_panel:reviews')


@staff_required
def review_reject(request, review_id):
    """Reject and delete a review"""
    review = get_object_or_404(Review, id=review_id)
    product = review.product
    product_name = product.name
    review_id_str = str(review.id)
    
    # Create audit log before deleting
    AuditLog.objects.create(
        actor=request.user,
        action='delete',
        entity_type='Review',
        entity_id=review_id_str,
        summary=f'Rejected review for {product_name}'
    )
    
    review.delete()
    
    # Recalculate product rating
    _recalculate_product_rating(product)
    
    messages.success(request, f'Review for {product_name} has been rejected and deleted.')
    return redirect('admin_panel:reviews')


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


# ============ DATA EXPORT ============

@staff_required
def import_export(request):
    """Data export view"""
    from django.http import HttpResponse
    import csv
    
    if request.method == 'POST' and 'export' in request.POST:
        export_type = request.POST.get('export_type')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{export_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        if export_type == 'products':
            writer.writerow(['SKU', 'Name', 'Category', 'Price', 'Stock', 'Reorder Threshold', 'Rating', 'Active', 'Created'])
            products = Product.objects.select_related('category').all().order_by('name')
            for product in products:
                writer.writerow([
                    product.sku,
                    product.name,
                    product.category.name,
                    product.price,
                    product.stock,
                    product.reorder_threshold,
                    product.rating,
                    product.is_active,
                    product.created_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        elif export_type == 'customers':
            writer.writerow(['ID', 'Username', 'Email', 'Name', 'Age', 'Gender', 'Monthly Income', 'Preferred Category', 'Created'])
            customers = Customer.objects.select_related('user').all().order_by('user__username')
            for customer in customers:
                writer.writerow([
                    customer.id,
                    customer.user.username,
                    customer.user.email,
                    customer.user.get_full_name() or '',
                    customer.age,
                    customer.gender,
                    customer.monthly_income_sgd,
                    customer.preferred_category or '',
                    customer.created_at.strftime('%Y-%m-%d %H:%M:%S') if customer.created_at else ''
                ])
        
        elif export_type == 'orders':
            writer.writerow(['Order ID', 'Customer', 'Status', 'Total Price', 'Shipping Address', 'Created', 'Updated'])
            orders = Order.objects.select_related('customer__user').all().order_by('-created_at')
            for order in orders:
                writer.writerow([
                    order.id,
                    order.customer.user.username,
                    order.get_status_display(),
                    order.total_price,
                    order.shipping_address,
                    order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    order.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                ])
        
        return response
    
    return render(request, 'admin_panel/data_export.html')


# ============ RECOMMENDATION PLACEMENT CONFIG ============

@staff_required
def recommendation_placement_list(request):
    """List and manage recommendation placements"""
    if request.method == 'POST' and 'toggle_active' in request.POST:
        placement_id = request.POST.get('placement_id')
        try:
            placement = RecommendationPlacement.objects.get(id=placement_id)
            placement.is_active = not placement.is_active
            placement.save()
            status = 'activated' if placement.is_active else 'deactivated'
            messages.success(request, f'Placement "{placement.title}" {status}.')
        except RecommendationPlacement.DoesNotExist:
            messages.error(request, 'Placement not found.')
        return redirect('admin_panel:recommendations')
    
    placements = RecommendationPlacement.objects.all().order_by('slug')
    
    context = {
        'placements': placements,
    }
    
    return render(request, 'admin_panel/recommendation_placements.html', context)


@staff_required
def preferred_category_analysis(request):
    """Preferred category analysis view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Preferred Category Analysis',
        'page_description': 'Analyze customer category preferences using ML'
    })


# ============ AUDIT LOGGING ============

@staff_required
def audit_log(request):
    """View audit logs with filters"""
    action_filter = request.GET.get('action', '')
    entity_type_filter = request.GET.get('entity_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    user_filter = request.GET.get('user', '')
    
    logs = AuditLog.objects.select_related('actor').all()
    
    # Apply filters
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if entity_type_filter:
        logs = logs.filter(entity_type=entity_type_filter)
    
    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            logs = logs.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            logs = logs.filter(created_at__lte=date_to_obj)
        except ValueError:
            pass
    
    if user_filter:
        logs = logs.filter(actor_id=user_filter)
    
    # Order by most recent first
    logs = logs.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin_users = User.objects.filter(is_staff=True).order_by('username')
    
    context = {
        'page_obj': page_obj,
        'selected_action': action_filter,
        'selected_entity_type': entity_type_filter,
        'selected_date_from': date_from,
        'selected_date_to': date_to,
        'selected_user': user_filter,
        'admin_users': admin_users,
        'action_choices': AuditLog.ACTION_CHOICES,
        'entity_types': AuditLog.objects.values_list('entity_type', flat=True).distinct().order_by('entity_type'),
    }
    
    return render(request, 'admin_panel/audit_log.html', context)


@staff_required
def admin_user_management(request):
    """Admin user management view - placeholder"""
    return render(request, 'admin_panel/placeholder.html', {
        'page_title': 'Admin User Management',
        'page_description': 'Manage admin users and permissions'
    })

