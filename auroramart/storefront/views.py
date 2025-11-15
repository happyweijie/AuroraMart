from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from decimal import Decimal
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Review, Watchlist, WatchlistItem
from users.models import Customer
from .forms import CheckoutForm, ReviewForm
from mlservices.get_recommendations import get_product_recommendations

# Create your views here.
def index(request):
    # Featured products with review counts for social proof
    featured_products = Product.objects.filter(
        stock__gte=0,
        is_active=True,
        archived=False
    ).annotate(
        review_count=Count('reviews', filter=Q(reviews__is_approved=True))
    ).order_by('-rating', '-review_count', '-created_at')[:12]

    # Get categories that have products (active and not archived) with product counts
    categories_with_products = Category.objects.filter(
        products__is_active=True,
        products__archived=False,
        products__stock__gte=0
    ).annotate(
        product_count=Count('products')
    ).distinct().order_by('-product_count', 'name')[:10]

    # for logged in users, include personalize products based on their preferences
    trending_products = None
    for_you_products = None
    
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        if customer.preferred_category_fk:
            preferred_category = customer.preferred_category_fk
            for_you_products = preferred_category.get_all_products().annotate(
                review_count=Count('reviews', filter=Q(reviews__is_approved=True))
            ).order_by('-rating', '-review_count', '-created_at')[:12]
    else:
        # For non-logged-in users, show trending products (highest rated or most reviewed)
        trending_products = Product.objects.filter(
            stock__gte=0,
            is_active=True,
            archived=False
        ).annotate(
            review_count=Count('reviews', filter=Q(reviews__is_approved=True))
        ).order_by('-rating', '-review_count', '-created_at')[:12]

    return render(request, 'storefront/home.html', {
        'featured_products': featured_products,
        'categories': categories_with_products,
        'for_you_products': for_you_products,
        'trending_products': trending_products,
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

    # Get all products in this category and its subcategories
    products = category_obj.get_all_products()
    
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
    if total_reviews > 0:
        average_rating = sum(review.rating for review in reviews) / total_reviews
        # Update product rating if different (only if there are approved reviews)
        if product.rating != average_rating:
            product.rating = round(average_rating, 2)
            product.save()
    else:
        average_rating = 0.0
    
    # Check if user can review (has purchased and hasn't reviewed yet)
    can_review = False
    has_purchased = False
    has_reviewed = False
    is_in_watchlist = False
    
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        # Check if user has purchased this product
        has_purchased = OrderItem.objects.filter(
            order__customer=customer,
            order__status='delivered',
            product=product
        ).exists()
        
        # Check if user has already reviewed this product
        has_reviewed = Review.objects.filter(
            customer=customer,
            product=product
        ).exists()
        
        can_review = has_purchased and not has_reviewed
        
        # Check if product is in watchlist
        try:
            watchlist = Watchlist.objects.get(customer=customer)
            is_in_watchlist = WatchlistItem.objects.filter(watchlist=watchlist, product=product).exists()
        except Watchlist.DoesNotExist:
            is_in_watchlist = False
    
    # use ml model to get similar items
    similar_items = get_product_recommendations([product.sku], top_n=4) 

    return render(request, 'storefront/product_detail.html', {
        'product': product,
        'similar_items': similar_items,
        'reviews': reviews,
        'total_reviews': total_reviews,
        'average_rating': average_rating,
        'can_review': can_review,
        'has_purchased': has_purchased,
        'has_reviewed': has_reviewed,
        'is_in_watchlist': is_in_watchlist,
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

    # recommendations based on cart items
    frequently_bought_together = []
    if cart_items:
        # Extract SKUs from cart items (handles both database cart items and session cart dicts)
        product_skus = [
            item.product.sku if hasattr(item, 'product') else item['product'].sku 
            for item in cart_items
        ]
        if product_skus:
            frequently_bought_together = get_product_recommendations(product_skus, top_n=3)
    else:
        # If cart is empty, show popular products instead
        frequently_bought_together = get_product_recommendations([], top_n=3)
    
    return render(request, 'storefront/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'using_db_cart': using_db_cart,
        'frequently_bought_together': frequently_bought_together,
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
    
    # Check which products can be reviewed (delivered orders only)
    reviewable_items = []
    if order.status == 'delivered' and hasattr(request.user, 'customer_profile'):
        for item in order.items.all():
            # Check if user has already reviewed this product
            has_reviewed = Review.objects.filter(
                customer=request.user.customer_profile,
                product=item.product
            ).exists()
            
            reviewable_items.append({
                'item': item,
                'can_review': not has_reviewed,
                'has_reviewed': has_reviewed,
            })
    
    return render(request, 'storefront/order_detail.html', {
        'order': order,
        'can_cancel': can_cancel,
        'reviewable_items': reviewable_items,
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


# ============ REVIEWS ============

@login_required
def review_create_view(request, sku):
    """Create a new review for a product"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to write reviews.')
        return redirect('storefront:product_detail', sku=sku)
    
    product = get_object_or_404(Product, sku=sku, is_active=True, archived=False)
    customer = request.user.customer_profile
    
    # Check if user has purchased this product
    has_purchased = OrderItem.objects.filter(
        order__customer=customer,
        order__status='delivered',
        product=product
    ).exists()
    
    if not has_purchased:
        messages.error(request, 'You must have purchased this product to write a review.')
        return redirect('storefront:product_detail', sku=sku)
    
    # Check if user has already reviewed this product
    existing_review = Review.objects.filter(customer=customer, product=product).first()
    if existing_review:
        messages.warning(request, 'You have already reviewed this product.')
        return redirect('storefront:product_detail', sku=sku)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.customer = customer
            review.is_approved = False  # Requires admin approval
            review.save()
            
            messages.success(request, 'Thank you for your review! It will be published after admin approval.')
            return redirect('storefront:product_detail', sku=sku)
    else:
        form = ReviewForm()
    
    return render(request, 'storefront/review_form.html', {
        'form': form,
        'product': product,
    })


@login_required
def review_list_view(request):
    """Display user's submitted reviews with status"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to view reviews.')
        return redirect('storefront:home')
    
    customer = request.user.customer_profile
    reviews = Review.objects.filter(customer=customer).select_related('product', 'product__category').order_by('-created_at')
    
    # Count reviews by status
    pending_count = reviews.filter(is_approved=False).count()
    approved_count = reviews.filter(is_approved=True).count()
    total_count = reviews.count()
    
    return render(request, 'storefront/review_list.html', {
        'reviews': reviews,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'total_count': total_count,
    })


# ============ WATCHLIST FUNCTIONALITY ============

def get_or_create_watchlist(customer):
    """Helper function to get or create a watchlist for a customer"""
    watchlist, created = Watchlist.objects.get_or_create(customer=customer)
    return watchlist


@login_required
def watchlist_view(request):
    """Display user's watchlist"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to access the watchlist.')
        return redirect('storefront:home')
    
    customer = request.user.customer_profile
    watchlist = get_or_create_watchlist(customer)
    watchlist_items = watchlist.items.select_related('product', 'product__category').order_by('-added_at')
    
    return render(request, 'storefront/watchlist.html', {
        'watchlist_items': watchlist_items,
        'watchlist_count': watchlist_items.count(),
    })


@login_required
def add_to_watchlist(request, sku):
    """Add a product to user's watchlist"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to add items to your watchlist.')
        return redirect('storefront:product_detail', sku=sku)
    
    product = get_object_or_404(Product, sku=sku, is_active=True, archived=False)
    customer = request.user.customer_profile
    watchlist = get_or_create_watchlist(customer)
    
    # Check if already in watchlist
    if WatchlistItem.objects.filter(watchlist=watchlist, product=product).exists():
        messages.info(request, f'{product.name} is already in your watchlist.')
    else:
        WatchlistItem.objects.create(watchlist=watchlist, product=product)
        messages.success(request, f'{product.name} has been added to your watchlist.')
    
    # Redirect back to product page or watchlist
    next_url = request.GET.get('next', 'storefront:product_detail')
    if next_url.startswith('http'):
        return redirect(next_url)
    elif ':' in next_url:
        from django.urls import reverse
        return redirect(reverse(next_url, args=[sku]))
    else:
        return redirect('storefront:product_detail', sku=sku)


@login_required
def remove_from_watchlist(request, sku):
    """Remove a product from user's watchlist"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to remove items from your watchlist.')
        return redirect('storefront:product_detail', sku=sku)
    
    product = get_object_or_404(Product, sku=sku)
    customer = request.user.customer_profile
    
    try:
        watchlist = Watchlist.objects.get(customer=customer)
        watchlist_item = WatchlistItem.objects.get(watchlist=watchlist, product=product)
        watchlist_item.delete()
        messages.success(request, f'{product.name} has been removed from your watchlist.')
    except (Watchlist.DoesNotExist, WatchlistItem.DoesNotExist):
        messages.error(request, 'Item not found in your watchlist.')
    
    # Redirect back based on referrer
    next_url = request.GET.get('next', 'storefront:watchlist')
    if next_url.startswith('http'):
        return redirect(next_url)
    elif ':' in next_url:
        from django.urls import reverse
        return redirect(reverse(next_url, args=[sku]))
    else:
        return redirect('storefront:watchlist')
