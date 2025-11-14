from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from decimal import Decimal
from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import CheckoutForm

# Create your views here.
def index(request):
    # replace wih ai recommendations later
    products = Product.objects.filter(
        stock__gte=0,
        is_active=True,
        archived=False) \
    .order_by('-rating', '-created_at') \
    .all()[:12]

    # Get categories that have products (active and not archived)
    categories_with_products = Category.objects.filter(
        products__is_active=True,
        products__archived=False,
        products__stock__gte=0
    ).annotate(
        product_count=Count('products')
    ).distinct().order_by('-product_count', 'name')[:10]

    # for logged in users, we can later personalize featured products based on their preferences
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        if customer.preferred_category_fk:
            preferred_category = customer.preferred_category_fk
            preferred_products = preferred_category.products.filter(
                stock__gte=0,
                is_active=True,
                archived=False
            ).order_by('-rating', '-created_at')[:12]
            if preferred_products.exists():
                products = preferred_products


    return render(request, 'storefront/home.html', {
        'featured_products': products,
        'categories': categories_with_products
        })

def products(request):
    # Get all filter parameters
    sort_by = request.GET.get('sort', 'rating')
    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    min_rating = request.GET.get('rating', '')
    
    # Base queryset
    products = Product.objects.filter(
        stock__gte=0,
        is_active=True,
        archived=False
    )
    
    # Apply search filter if query exists
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Apply category filter
    if category_filter:
        products = products.filter(category__slug=category_filter)
    
    # Apply price range filter
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    # Apply rating filter
    if min_rating:
        try:
            products = products.filter(rating__gte=float(min_rating))
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'price-low':
        products = products.order_by('price', '-rating')
    elif sort_by == 'price-high':
        products = products.order_by('-price', '-rating')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:  # Default to 'rating'
        products = products.order_by('-rating', '-created_at')
    
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all categories for filter dropdown
    all_categories = Category.objects.filter(
        products__is_active=True,
        products__archived=False
    ).distinct().order_by('name')

    return render(request, 'storefront/products.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'all_categories': all_categories,
        'selected_category': category_filter,
        'min_price': min_price,
        'max_price': max_price,
        'min_rating': min_rating,
    })

def category(request, slug):    
    # Get all filter parameters
    sort_by = request.GET.get('sort', 'rating')
    search_query = request.GET.get('q', '').strip()
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    min_rating = request.GET.get('rating', '')
    
    # Get category object
    category_obj = Category.objects.get(slug=slug)
    
    # Base queryset
    products = category_obj.products.filter(
        stock__gte=0,
        is_active=True,
        archived=False
    )
    
    # Apply search filter if query exists
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Apply price range filter
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    # Apply rating filter
    if min_rating:
        try:
            products = products.filter(rating__gte=float(min_rating))
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'price-low':
        products = products.order_by('price', '-rating')
    elif sort_by == 'price-high':
        products = products.order_by('-price', '-rating')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    else:  # Default to 'rating'
        products = products.order_by('-rating', '-created_at')
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'storefront/products.html', {
        'page_obj': page_obj,
        'category_name': category_obj.name,
        'category_slug': slug,
        'search_query': search_query,
        'sort_by': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'min_rating': min_rating,
    })

def product_detail(request, sku):
    """Display detailed product information including reviews"""
    product = get_object_or_404(
        Product.objects.select_related('category'),
        sku=sku,
        is_active=True,
        archived=False
    )
    
    # Get approved reviews for this product
    reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    
    # Calculate review statistics
    total_reviews = reviews.count()
    
    return render(request, 'storefront/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'total_reviews': total_reviews,
    })


# ============ CART FUNCTIONALITY ============

def get_cart_items(request):
    """Helper function to get cart items for both authenticated and guest users"""
    cart_items = []
    total = Decimal('0.00')
    
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        # Use database cart for authenticated users
        cart, created = Cart.objects.get_or_create(customer=request.user.customer_profile)
        cart_items = cart.items.select_related('product').all()
        for item in cart_items:
            item.subtotal = item.product.price * item.quantity
            total += item.subtotal
    else:
        # Use session cart for guest users
        session_cart = request.session.get('cart', {})
        for sku, quantity in session_cart.items():
            try:
                product = Product.objects.get(sku=sku, is_active=True, archived=False)
                if product.stock >= quantity:
                    subtotal = product.price * quantity
                    cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'subtotal': subtotal
                    })
                    total += subtotal
            except Product.DoesNotExist:
                pass
    
    return cart_items, total


def add_to_cart(request, sku):
    """Add a product to the cart (session or database)"""
    product = get_object_or_404(Product, sku=sku, is_active=True, archived=False)
    quantity = int(request.POST.get('quantity', 1))
    
    # Check stock availability
    if product.stock < quantity:
        messages.error(request, f'Sorry, only {product.stock} units available.')
        return redirect('storefront:product_detail', sku=sku)
    
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        # Use database cart for authenticated users
        cart, created = Cart.objects.get_or_create(customer=request.user.customer_profile)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        if not created:
            # Item already exists, update quantity
            new_quantity = cart_item.quantity + quantity
            if product.stock >= new_quantity:
                cart_item.quantity = new_quantity
                cart_item.save()
            else:
                messages.error(request, f'Cannot add more. Only {product.stock} units available.')
                return redirect('storefront:product_detail', sku=sku)
        else:
            cart_item.quantity = quantity
            cart_item.save()
        
        messages.success(request, f'{product.name} added to cart!')
    else:
        # Use session cart for guest users
        cart = request.session.get('cart', {})
        
        if sku in cart:
            new_quantity = cart[sku] + quantity
            if product.stock >= new_quantity:
                cart[sku] = new_quantity
            else:
                messages.error(request, f'Cannot add more. Only {product.stock} units available.')
                return redirect('storefront:product_detail', sku=sku)
        else:
            cart[sku] = quantity
        
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, f'{product.name} added to cart!')
    
    # Redirect based on where the request came from
    next_url = request.GET.get('next', 'storefront:cart')
    return redirect(next_url)


def cart_view(request):
    """Display the shopping cart"""
    cart_items, total = get_cart_items(request)
    
    # Determine if using database cart (only if user is authenticated AND has customer_profile)
    using_db_cart = request.user.is_authenticated and hasattr(request.user, 'customer_profile')
    
    return render(request, 'storefront/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'using_db_cart': using_db_cart,
    })


def update_cart_item(request, item_id=None):
    """Update quantity of a cart item"""
    if request.method != 'POST':
        return redirect('storefront:cart')
    
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity < 1:
        messages.error(request, 'Quantity must be at least 1.')
        return redirect('storefront:cart')
    
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        # Update database cart
        cart_item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user.customer_profile)
        
        if cart_item.product.stock >= quantity:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated!')
        else:
            messages.error(request, f'Only {cart_item.product.stock} units available.')
    else:
        # Update session cart
        sku = request.POST.get('sku')
        cart = request.session.get('cart', {})
        
        if sku in cart:
            try:
                product = Product.objects.get(sku=sku)
                if product.stock >= quantity:
                    cart[sku] = quantity
                    request.session['cart'] = cart
                    request.session.modified = True
                    messages.success(request, 'Cart updated!')
                else:
                    messages.error(request, f'Only {product.stock} units available.')
            except Product.DoesNotExist:
                pass
    
    return redirect('storefront:cart')


def remove_from_cart(request, item_id=None):
    """Remove an item from the cart"""
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        # Remove from database cart
        cart_item = get_object_or_404(CartItem, id=item_id, cart__customer=request.user.customer_profile)
        product_name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f'{product_name} removed from cart.')
    else:
        # Remove from session cart
        sku = request.GET.get('sku')
        cart = request.session.get('cart', {})
        
        if sku in cart:
            try:
                product = Product.objects.get(sku=sku)
                product_name = product.name
                del cart[sku]
                request.session['cart'] = cart
                request.session.modified = True
                messages.success(request, f'{product_name} removed from cart.')
            except Product.DoesNotExist:
                pass
    
    return redirect('storefront:cart')


# ============ CHECKOUT & ORDERS ============

@login_required
def checkout_view(request):
    """Display checkout form and handle order creation"""
    # Check if user has customer profile
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to checkout.')
        return redirect('storefront:cart')
    
    # Get cart items
    cart_items, total = get_cart_items(request)
    
    # Check if cart is empty
    if not cart_items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('storefront:cart')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Create order with transaction to ensure data consistency
            try:
                with transaction.atomic():
                    # Create the order
                    order = Order.objects.create(
                        customer=request.user.customer_profile,
                        status='pending',
                        total_price=total,
                        shipping_address=form.get_formatted_address()
                    )
                    
                    # Create order items from cart
                    for item in cart_items:
                        # Check stock availability
                        product = item.product if hasattr(item, 'product') else item['product']
                        quantity = item.quantity if hasattr(item, 'quantity') else item['quantity']
                        
                        if product.stock < quantity:
                            raise ValueError(f'Insufficient stock for {product.name}')
                        
                        # Create order item
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            unit_price=product.price
                        )
                        
                        # Reduce product stock
                        product.stock -= quantity
                        product.save()
                    
                    # Clear the cart
                    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
                        # Clear database cart
                        cart = Cart.objects.filter(customer=request.user.customer_profile).first()
                        if cart:
                            cart.items.all().delete()
                    else:
                        # Clear session cart
                        request.session['cart'] = {}
                        request.session.modified = True
                    
                    messages.success(request, f'Order #{order.id} placed successfully!')
                    return redirect('storefront:order_confirmation', order_id=order.id)
                    
            except ValueError as e:
                messages.error(request, str(e))
                return redirect('storefront:cart')
            except Exception as e:
                messages.error(request, 'An error occurred while processing your order. Please try again.')
                return redirect('storefront:checkout')
    else:
        form = CheckoutForm()
    
    return render(request, 'storefront/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total': total,
    })


@login_required
def order_confirmation_view(request, order_id):
    """Display order confirmation"""
    order = get_object_or_404(Order, id=order_id, customer=request.user.customer_profile)
    
    return render(request, 'storefront/order_confirmation.html', {
        'order': order,
    })


@login_required
def order_list_view(request):
    """Display user's order history"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to view orders.')
        return redirect('storefront:home')
    
    orders = Order.objects.filter(customer=request.user.customer_profile).order_by('-created_at')
    
    return render(request, 'storefront/order_list.html', {
        'orders': orders,
    })


@login_required
def order_detail_view(request, order_id):
    """Display detailed view of a single order"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to view orders.')
        return redirect('storefront:home')
    
    order = get_object_or_404(Order, id=order_id, customer=request.user.customer_profile)
    
    # Check if order can be cancelled (< 24 hours old and status is pending)
    from django.utils import timezone
    from datetime import timedelta
    
    can_cancel = (
        order.status == 'pending' and 
        order.created_at >= timezone.now() - timedelta(hours=24)
    )
    
    return render(request, 'storefront/order_detail.html', {
        'order': order,
        'can_cancel': can_cancel,
    })


@login_required
def cancel_order_view(request, order_id):
    """Cancel an order if eligible"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to cancel orders.')
        return redirect('storefront:home')
    
    order = get_object_or_404(Order, id=order_id, customer=request.user.customer_profile)
    
    # Check if order can be cancelled
    from django.utils import timezone
    from datetime import timedelta
    
    if order.status != 'pending':
        messages.error(request, 'Only pending orders can be cancelled.')
        return redirect('storefront:order_detail', order_id=order_id)
    
    if order.created_at < timezone.now() - timedelta(hours=24):
        messages.error(request, 'Orders can only be cancelled within 24 hours of placement.')
        return redirect('storefront:order_detail', order_id=order_id)
    
    # Cancel the order and restore stock
    with transaction.atomic():
        order.status = 'cancelled'
        order.save()
        
        # Restore product stock
        for item in order.items.all():
            item.product.stock += item.quantity
            item.product.save()
    
    messages.success(request, f'Order #{order.id} has been cancelled.')
    return redirect('storefront:order_list')
