from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, F, Q, Avg, Count, Case, When, IntegerField
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from storefront.models import Product, Order, OrderItem, Category, Review, ChatSession, ChatMessage, Promotion, AiChatSession, AiChatMessage
from users.models import Customer, User
from admin_panel.models import RecommendationPlacement, AnalyticsMetric, AuditLog
from .decorators import staff_required
from .forms import ProductForm, CategoryForm, BulkInventoryUpdateForm, CustomerForm, OrderStatusUpdateForm, PromotionForm, AdminUserForm, AdminUserCreateForm

def index(request):
    """Redirect to admin login or dashboard based on authentication"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_panel:dashboard')
    else:
        return redirect('admin_panel:admin_login')
    
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
            messages.success(request, f'Product \"{product.name}\" created successfully!')
            # Redirect to the product list view (named \"products\" in urls.py)
            return redirect('admin_panel:products')
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
            # Redirect back to product list (URL name is 'products')
            return redirect('admin_panel:products')
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
        messages.success(request, f'Product \"{product_name}\" has been archived.')
        # Redirect back to product list (URL name is 'products')
        return redirect('admin_panel:products')
    
    return render(request, 'admin_panel/product_confirm_delete.html', {
        'product': product
    })


# Alias for backward compatibility
@staff_required
def product_management(request):
    """Redirect to product list"""
    # Use the current URL name for product listing (named 'products' in urls.py)
    return redirect('admin_panel:products')


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
            return redirect('admin_panel:categories')
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
            return redirect('admin_panel:categories')
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
    return redirect('admin_panel:categories')


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


# Pricing Management removed - pricing can be managed through Product Management


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
            # Redirect back to customer list (URL name is 'customers')
            return redirect('admin_panel:customers')
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
    # Use the current URL name for customer listing (named 'customers' in urls.py)
    return redirect('admin_panel:customers')


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
    # Use the current URL name for order listing (named 'orders' in urls.py)
    return redirect('admin_panel:orders')


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


# ============ PROMOTION MANAGEMENT ============

@staff_required
def promotion_list(request):
    """List all promotions"""
    promotions = Promotion.objects.all().order_by('-start_date')
    
    # Filtering
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    if status_filter == 'active':
        today = timezone.now().date()
        promotions = promotions.filter(is_active=True, start_date__lte=today, end_date__gte=today)
    elif status_filter == 'inactive':
        promotions = promotions.filter(is_active=False)
    elif status_filter == 'upcoming':
        today = timezone.now().date()
        promotions = promotions.filter(start_date__gt=today)
    elif status_filter == 'expired':
        today = timezone.now().date()
        promotions = promotions.filter(end_date__lt=today)
    
    if search_query:
        promotions = promotions.filter(name__icontains=search_query)
    
    # Pagination
    paginator = Paginator(promotions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_panel/promotion_list.html', context)


@staff_required
def promotion_create(request):
    """Create a new promotion"""
    if request.method == 'POST':
        form = PromotionForm(request.POST)
        if form.is_valid():
            promotion = form.save()
            # Create audit log
            AuditLog.objects.create(
                actor=request.user,
                action='create',
                entity_type='Promotion',
                entity_id=str(promotion.id),
                summary=f'Created promotion: {promotion.name}'
            )
            messages.success(request, f'Promotion "{promotion.name}" created successfully.')
            return redirect('admin_panel:promotions')
    else:
        form = PromotionForm()
    
    context = {
        'form': form,
        'page_title': 'Create Promotion',
    }
    
    return render(request, 'admin_panel/promotion_form.html', context)


@staff_required
def promotion_update(request, promotion_id):
    """Update an existing promotion"""
    try:
        promotion = Promotion.objects.get(id=promotion_id)
    except Promotion.DoesNotExist:
        messages.error(request, 'Promotion not found.')
        return redirect('admin_panel:promotions')
    
    if request.method == 'POST':
        form = PromotionForm(request.POST, instance=promotion)
        if form.is_valid():
            form.save()
            # Create audit log
            AuditLog.objects.create(
                actor=request.user,
                action='update',
                entity_type='Promotion',
                entity_id=str(promotion.id),
                summary=f'Updated promotion: {promotion.name}'
            )
            messages.success(request, f'Promotion "{promotion.name}" updated successfully.')
            return redirect('admin_panel:promotions')
    else:
        form = PromotionForm(instance=promotion)
    
    context = {
        'form': form,
        'promotion': promotion,
        'page_title': 'Edit Promotion',
    }
    
    return render(request, 'admin_panel/promotion_form.html', context)


@staff_required
def promotion_delete(request, promotion_id):
    """Delete a promotion"""
    try:
        promotion = Promotion.objects.get(id=promotion_id)
    except Promotion.DoesNotExist:
        messages.error(request, 'Promotion not found.')
        return redirect('admin_panel:promotions')
    
    if request.method == 'POST':
        promotion_name = promotion.name
        promotion.delete()
        # Create audit log
        AuditLog.objects.create(
            actor=request.user,
            action='delete',
            entity_type='Promotion',
            entity_id=str(promotion_id),
            summary=f'Deleted promotion: {promotion_name}'
        )
        messages.success(request, f'Promotion "{promotion_name}" deleted successfully.')
        return redirect('admin_panel:promotions')
    
    context = {
        'promotion': promotion,
    }
    
    return render(request, 'admin_panel/promotion_confirm_delete.html', context)


@staff_required
def chat_support(request):
    """Admin chat support management"""
    status_filter = request.GET.get('status', 'open')  # open, closed, all
    search_query = request.GET.get('q', '').strip()
    
    # Base queryset
    chat_sessions = ChatSession.objects.select_related('customer', 'customer__user', 'order').prefetch_related('messages').all()
    
    # Apply status filter
    if status_filter == 'open':
        chat_sessions = chat_sessions.filter(status='open')
    elif status_filter == 'closed':
        chat_sessions = chat_sessions.filter(status='closed')
    # 'all' shows everything
    
    # Apply search filter
    if search_query:
        chat_sessions = chat_sessions.filter(
            Q(subject__icontains=search_query) |
            Q(customer__user__username__icontains=search_query) |
            Q(customer__user__email__icontains=search_query)
        )
    
    # Order by most recent first
    chat_sessions = chat_sessions.order_by('-updated_at')
    
    # Counts for status badges
    open_count = ChatSession.objects.filter(status='open').count()
    closed_count = ChatSession.objects.filter(status='closed').count()
    total_count = ChatSession.objects.count()
    
    # Pagination
    paginator = Paginator(chat_sessions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'open_count': open_count,
        'closed_count': closed_count,
        'total_count': total_count,
    }
    
    return render(request, 'admin_panel/chat_support.html', context)


@staff_required
def chat_detail_admin(request, session_id):
    """Admin view and reply to chat session"""
    chat_session = get_object_or_404(ChatSession.objects.select_related('customer', 'customer__user', 'order'), id=session_id)
    
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        action = request.POST.get('action', '')
        
        if action == 'close':
            chat_session.status = 'closed'
            chat_session.save()
            messages.success(request, 'Chat session closed.')
            return redirect('admin_panel:chat')
        
        if message_text:
            ChatMessage.objects.create(
                session=chat_session,
                sender='admin',
                message=message_text
            )
            chat_session.save()  # Update updated_at
            messages.success(request, 'Message sent.')
            return redirect('admin_panel:chat_detail', session_id=session_id)
    
    # Get all messages
    messages_list = chat_session.messages.all().order_by('created_at')
    
    return render(request, 'admin_panel/chat_detail.html', {
        'chat_session': chat_session,
        'messages_list': messages_list,
    })


# ============ DATA EXPORT ============

@staff_required
def import_export(request):
    """Data import/export view"""
    from django.http import HttpResponse
    from django.db import transaction
    import csv
    import io
    from users.models import Customer
    from storefront.models import Category
    from decimal import Decimal
    
    # Handle CSV Import
    if request.method == 'POST' and 'import' in request.POST:
        import_type = request.POST.get('import_type')
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return render(request, 'admin_panel/data_export.html')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return render(request, 'admin_panel/data_export.html')
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            success_count = 0
            error_count = 0
            errors = []
            
            if import_type == 'customers':
                with transaction.atomic():
                    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                        try:
                            # Get or create User first
                            username = row.get('Username', '').strip()
                            email = row.get('Email', '').strip()
                            
                            if not username or not email:
                                errors.append(f"Row {row_num}: Username and Email are required")
                                error_count += 1
                                continue
                            
                            # Check if user already exists
                            user, user_created = User.objects.get_or_create(
                                username=username,
                                defaults={
                                    'email': email,
                                    'first_name': row.get('First Name', '').strip(),
                                    'last_name': row.get('Last Name', '').strip(),
                                }
                            )
                            
                            if not user_created:
                                # Update email if different
                                if user.email != email:
                                    user.email = email
                                    user.save()
                            
                            # Get or create Customer
                            customer, customer_created = Customer.objects.get_or_create(
                                user=user,
                                defaults={
                                    'age': int(row.get('Age', 0)) or 25,
                                    'household_size': int(row.get('Household Size', 0)) or 1,
                                    'has_children': row.get('Has Children', 'False').strip().lower() == 'true',
                                    'monthly_income_sgd': Decimal(row.get('Monthly Income', 0)) or Decimal('0.00'),
                                    'gender': row.get('Gender', 'Male').strip(),
                                    'employment_status': row.get('Employment Status', 'Full-Time').strip(),
                                    'occupation': row.get('Occupation', 'Tech').strip(),
                                    'education': row.get('Education', 'Bachelor').strip(),
                                }
                            )
                            
                            # Update preferred category if provided
                            preferred_cat = row.get('Preferred Category', '').strip()
                            if preferred_cat:
                                try:
                                    category = Category.objects.filter(
                                        Q(name__iexact=preferred_cat) |
                                        Q(slug__iexact=preferred_cat.replace(' ', '-'))
                                    ).first()
                                    if category:
                                        customer.preferred_category_fk = category
                                        customer.preferred_category = category.name
                                        customer.save(update_fields=['preferred_category_fk', 'preferred_category'])
                                except Exception:
                                    pass
                            
                            success_count += 1
                            
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Row {row_num}: {str(e)}")
                            continue
                
                if success_count > 0:
                    messages.success(request, f'Successfully imported {success_count} customer(s).')
                if error_count > 0:
                    messages.warning(request, f'Failed to import {error_count} row(s). Please check the format.')
                    if errors:
                        # Show first 5 errors
                        for error in errors[:5]:
                            messages.error(request, error)
            
            return redirect('admin_panel:import_export')
            
        except Exception as e:
            messages.error(request, f'Error importing CSV: {str(e)}')
            return render(request, 'admin_panel/data_export.html')
    
    # Handle CSV Export
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
            writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Age', 'Gender', 'Household Size', 'Has Children', 'Monthly Income', 'Employment Status', 'Occupation', 'Education', 'Preferred Category', 'Created'])
            customers = Customer.objects.select_related('user').all().order_by('user__username')
            for customer in customers:
                writer.writerow([
                    customer.user.username,
                    customer.user.email,
                    customer.user.first_name or '',
                    customer.user.last_name or '',
                    customer.age,
                    customer.gender,
                    customer.household_size,
                    customer.has_children,
                    customer.monthly_income_sgd,
                    customer.employment_status,
                    customer.occupation,
                    customer.education,
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
    """Preferred category analysis view with ML insights"""
    from users.models import Customer
    from storefront.models import Category
    from mlservices.predict_preferred_category import predict_preferred_category
    from django.db.models import Count, Q
    
    # Handle bulk prediction update
    if request.method == 'POST' and 'update_predictions' in request.POST:
        # Get customers without preferred_category_fk
        customers_to_update = Customer.objects.filter(preferred_category_fk__isnull=True)
        updated_count = 0
        
        for customer in customers_to_update:
            try:
                # Prepare customer data for ML prediction
                customer_data = {
                    'age': customer.age,
                    'household_size': customer.household_size,
                    'has_children': 1 if customer.has_children else 0,
                    'monthly_income_sgd': float(customer.monthly_income_sgd),
                    'gender': customer.gender,
                    'employment_status': customer.employment_status,
                    'occupation': customer.occupation,
                    'education': customer.education,
                }
                
                # Get prediction
                prediction = predict_preferred_category(customer_data)
                predicted_category_name = prediction[0] if len(prediction) > 0 else None
                
                # Find matching category
                if predicted_category_name:
                    try:
                        category = Category.objects.filter(
                            Q(name__iexact=predicted_category_name) |
                            Q(slug__iexact=predicted_category_name.replace(' ', '-'))
                        ).first()
                        
                        if category:
                            customer.preferred_category_fk = category
                            customer.preferred_category = category.name
                            customer.save(update_fields=['preferred_category_fk', 'preferred_category'])
                            updated_count += 1
                    except Exception as e:
                        continue
            except Exception as e:
                continue
        
        messages.success(request, f'Updated preferred category predictions for {updated_count} customers.')
        return redirect('admin_panel:preferred_category')
    
    # Get statistics
    total_customers = Customer.objects.count()
    customers_with_preferred = Customer.objects.filter(preferred_category_fk__isnull=False).count()
    customers_without_preferred = total_customers - customers_with_preferred
    
    # Category distribution
    category_distribution = Category.objects.annotate(
        customer_count=Count('customers_preferred')
    ).filter(customer_count__gt=0).order_by('-customer_count')
    
    # Get customers by category
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('search', '').strip()
    
    customers = Customer.objects.select_related('user', 'preferred_category_fk').all()
    
    if category_filter:
        try:
            category = Category.objects.get(id=category_filter)
            customers = customers.filter(preferred_category_fk=category)
        except Category.DoesNotExist:
            pass
    
    if search_query:
        customers = customers.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(customers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_customers': total_customers,
        'customers_with_preferred': customers_with_preferred,
        'customers_without_preferred': customers_without_preferred,
        'category_distribution': category_distribution,
        'selected_category': category_filter,
        'search_query': search_query,
        'all_categories': Category.objects.all().order_by('name'),
    }
    
    return render(request, 'admin_panel/preferred_category_analysis.html', context)


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


# ============ ADMIN USER MANAGEMENT ============

@staff_required
def admin_user_list(request):
    """List all admin users"""
    # Only show users with is_staff=True
    users = User.objects.filter(is_staff=True).order_by('username')
    
    # Filtering
    role_filter = request.GET.get('role', 'all')
    search_query = request.GET.get('search', '')
    
    if role_filter == 'superuser':
        users = users.filter(is_superuser=True)
    elif role_filter == 'staff':
        users = users.filter(is_superuser=False)
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
    }
    
    return render(request, 'admin_panel/admin_user_list.html', context)


@staff_required
def admin_user_create(request):
    """Create a new admin user"""
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create audit log
            AuditLog.objects.create(
                actor=request.user,
                action='create',
                entity_type='Admin User',
                entity_id=str(user.id),
                summary=f'Created admin user: {user.username}'
            )
            messages.success(request, f'Admin user "{user.username}" created successfully.')
            return redirect('admin_panel:admin_users')
    else:
        form = AdminUserCreateForm()
    
    context = {
        'form': form,
        'page_title': 'Create Admin User',
    }
    
    return render(request, 'admin_panel/admin_user_form.html', context)


@staff_required
def admin_user_update(request, user_id):
    """Update an existing admin user"""
    try:
        user = User.objects.get(id=user_id, is_staff=True)
    except User.DoesNotExist:
        messages.error(request, 'Admin user not found.')
        return redirect('admin_panel:admin_users')
    
    # Prevent users from removing their own staff status
    if request.user.id == user.id and request.method == 'POST':
        if 'is_staff' in request.POST and not request.POST.get('is_staff'):
            messages.error(request, 'You cannot remove your own staff status.')
            return redirect('admin_panel:admin_user_update', user_id=user_id)
    
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            # Create audit log
            AuditLog.objects.create(
                actor=request.user,
                action='update',
                entity_type='Admin User',
                entity_id=str(user.id),
                summary=f'Updated admin user: {user.username}'
            )
            messages.success(request, f'Admin user "{user.username}" updated successfully.')
            return redirect('admin_panel:admin_users')
    else:
        form = AdminUserForm(instance=user)
    
    context = {
        'form': form,
        'admin_user': user,
        'page_title': 'Edit Admin User',
    }
    
    return render(request, 'admin_panel/admin_user_form.html', context)


@staff_required
def admin_user_delete(request, user_id):
    """Delete an admin user"""
    try:
        user = User.objects.get(id=user_id, is_staff=True)
    except User.DoesNotExist:
        messages.error(request, 'Admin user not found.')
        return redirect('admin_panel:admin_users')
    
    # Prevent users from deleting themselves
    if request.user.id == user.id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('admin_panel:admin_users')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        # Create audit log
        AuditLog.objects.create(
            actor=request.user,
            action='delete',
            entity_type='Admin User',
            entity_id=str(user_id),
            summary=f'Deleted admin user: {username}'
        )
        messages.success(request, f'Admin user "{username}" deleted successfully.')
        return redirect('admin_panel:admin_users')
    
    context = {
        'admin_user': user,
    }
    
    return render(request, 'admin_panel/admin_user_confirm_delete.html', context)

@staff_required
def aurora_chatbot_logs(request):
    # Chatbot sessions
    sessions = AiChatSession.objects.order_by("-updated_at")
    paginator = Paginator(sessions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "admin_panel/aurora_chatbot_logs.html", {
        "page_obj": page_obj,
    })
