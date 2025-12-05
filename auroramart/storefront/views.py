from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from .models import Product, Category, Cart, CartItem, Order, OrderItem, Review, Watchlist, WatchlistItem, Promotion, ChatSession, ChatMessage, AiChatSession, AiChatMessage
from users.models import Customer
from .forms import CheckoutForm, ReviewForm, ChatForm, ChatMessageForm
from mlservices.get_recommendations import get_product_recommendations
from admin_panel.models import RecommendationPlacement

# Helper function to annotate products with promotion data
def annotate_products_with_promotions(products):
    """Add promotion data directly to product objects (modifies in place)"""
    today = date.today()
    all_active_promotions = Promotion.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).prefetch_related('products', 'categories')
    
    # Handle different input types
    if hasattr(products, 'object_list'):  # Paginator Page object
        products_list = list(products.object_list)
    elif hasattr(products, '__iter__'):  # Queryset or list
        products_list = list(products)
    else:
        products_list = [products]
    
    for product in products_list:
        applicable_promotions = []
        for promotion in all_active_promotions:
            if promotion.applies_to_product(product):
                applicable_promotions.append(promotion)
        
        # Sort by discount percent (highest first) and get the best one
        if applicable_promotions:
            applicable_promotions.sort(key=lambda p: p.discount_percent, reverse=True)
            best_promotion = applicable_promotions[0]
            discount_amount = (product.price * best_promotion.discount_percent) / 100
            discounted_price = product.price - discount_amount
            
            # Attach promotion data directly to product object
            product.active_promotion = best_promotion
            product.discounted_price = discounted_price
            product.is_flash_sale = (best_promotion.end_date - today).days <= 3
        else:
            product.active_promotion = None
            product.discounted_price = None
            product.is_flash_sale = False
    
    # If it was a page object, update its object_list
    if hasattr(products, 'object_list'):
        products.object_list = products_list
    
    return products if hasattr(products, 'object_list') else products_list

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
    
    # Annotate homepage categories with flash sale data
    today = date.today()
    flash_sale_promotions = Promotion.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).prefetch_related('categories')
    
    flash_sale_data = {}
    for promotion in flash_sale_promotions:
        days_remaining = (promotion.end_date - today).days
        if days_remaining <= 3:  # Flash sale (3 days or less)
            for category in promotion.categories.all():
                if category.id not in flash_sale_data or days_remaining < (flash_sale_data[category.id]['end_date'] - today).days:
                    flash_sale_data[category.id] = {
                        'promotion': promotion,
                        'end_date': promotion.end_date,
                        'discount': promotion.discount_percent
                    }
    
    # Annotate categories with flash sale info
    for category in categories_with_products:
        if category.id in flash_sale_data:
            category.has_flash_sale = True
            category.flash_sale_promotion = flash_sale_data[category.id]['promotion']
            category.flash_sale_end_date = flash_sale_data[category.id]['end_date']
            category.flash_sale_discount = flash_sale_data[category.id]['discount']
        else:
            category.has_flash_sale = False
            category.flash_sale_promotion = None
            category.flash_sale_end_date = None
            category.flash_sale_discount = None

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

    # Annotate products with promotion data (convert querysets to lists first)
    featured_products = list(featured_products)
    featured_products = annotate_products_with_promotions(featured_products)
    if for_you_products:
        for_you_products = list(for_you_products)
        for_you_products = annotate_products_with_promotions(for_you_products)
    if trending_products:
        trending_products = list(trending_products)
        trending_products = annotate_products_with_promotions(trending_products)
    
    # Check if recommendation placement is active for homepage
    homepage_recommendations = None
    recommendation_placement = RecommendationPlacement.objects.filter(
        placement='homepage',
        is_active=True
    ).first()
    
    if recommendation_placement and recommendation_placement.strategy == 'association_rules':
        # Get ML recommendations for homepage (e.g., based on popular products)
        popular_skus = [p.sku for p in featured_products[:5]] if featured_products else []
        homepage_recommendations = list(get_product_recommendations(popular_skus, top_n=8))
        homepage_recommendations = annotate_products_with_promotions(homepage_recommendations)

    return render(request, 'storefront/home.html', {
        'featured_products': featured_products,
        'categories': categories_with_products,
        'for_you_products': for_you_products,
        'trending_products': trending_products,
        'homepage_recommendations': homepage_recommendations,
        'recommendation_placement': recommendation_placement,
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

    # Annotate products with promotion data (modifies page_obj in place)
    annotate_products_with_promotions(page_obj)

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
    
    # Annotate products with promotion data (modifies page_obj in place)
    annotate_products_with_promotions(page_obj)
    
    # Check if recommendation placement is active for category page
    category_recommendations = None
    recommendation_placement = RecommendationPlacement.objects.filter(
        placement='category',
        is_active=True
    ).first()
    
    if recommendation_placement and recommendation_placement.strategy == 'association_rules':
        # Get ML recommendations based on category products
        # page_obj.object_list may be a list after promotion annotation, so avoid values_list
        if hasattr(page_obj, 'object_list'):
            first_products = list(page_obj.object_list)[:5]
            category_product_skus = [p.sku for p in first_products]
        else:
            category_product_skus = []
        if category_product_skus:
            category_recommendations = list(get_product_recommendations(category_product_skus, top_n=6))
            category_recommendations = annotate_products_with_promotions(category_recommendations)

    return render(request, 'storefront/products.html', {
        'page_obj': page_obj,
        'category_name': category_obj.name,
        'category_slug': slug,
        'search_query': search_query,
        'sort_by': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'min_rating': min_rating,
        'category_recommendations': category_recommendations,
        'recommendation_placement': recommendation_placement,
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
    
    # Get active promotions for this product
    # Priority: Product-specific promotions > Category-based promotions
    today = date.today()
    all_active_promotions = Promotion.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).prefetch_related('products', 'categories')
    
    # Filter promotions that apply to this product
    applicable_promotions = []
    for promotion in all_active_promotions:
        if promotion.applies_to_product(product):
            applicable_promotions.append(promotion)
    
    # Sort by discount percent (highest first) and get the best one
    applicable_promotions.sort(key=lambda p: p.discount_percent, reverse=True)
    
    # Calculate discounted price if promotion exists
    discounted_price = None
    active_promotion = None
    if applicable_promotions:
        active_promotion = applicable_promotions[0]
        discount_amount = (product.price * active_promotion.discount_percent) / 100
        discounted_price = product.price - discount_amount
    
    # Check if recommendation placement is active for product detail page
    similar_items = []
    recommendation_placement = RecommendationPlacement.objects.filter(
        placement='product_detail',
        is_active=True
    ).first()
    
    if recommendation_placement:
        # Use ML recommendations if placement is active
        if recommendation_placement.strategy == 'association_rules':
            similar_items = get_product_recommendations([product.sku], top_n=4) 
            annotate_products_with_promotions(similar_items)

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
        'active_promotion': active_promotion,
        'discounted_price': discounted_price,
        'recommendation_placement': recommendation_placement,
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

        # Annotate products in the cart with any active promotions
        products = [item.product for item in cart_items]
        annotate_products_with_promotions(products)

        for item in cart_items:
            # Use discounted price if available, otherwise regular price
            effective_price = getattr(item.product, 'discounted_price', None) or item.product.price
            item.unit_price = effective_price
            item.original_price = item.product.price
            item.subtotal = effective_price * item.quantity
            total += item.subtotal
    else:
        # Use session cart for guest users
        session_cart = request.session.get('cart', {})
        session_items = []

        for sku, quantity in session_cart.items():
            try:
                product = Product.objects.get(sku=sku, is_active=True, archived=False)
                if product.stock >= quantity:
                    session_items.append((product, quantity))
            except Product.DoesNotExist:
                pass

        # Annotate all session-cart products with promotions in one go
        products = [p for (p, _) in session_items]
        annotate_products_with_promotions(products)

        for product, quantity in session_items:
            effective_price = getattr(product, 'discounted_price', None) or product.price
            subtotal = effective_price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'unit_price': effective_price,
                'original_price': product.price,
                'subtotal': subtotal,
            })
            total += subtotal
    
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

    # Check if recommendation placement is active for cart page
    frequently_bought_together = []
    recommendation_placement = RecommendationPlacement.objects.filter(
        placement='cart',
        is_active=True
    ).first()
    
    if recommendation_placement:
        if cart_items:
            # Extract SKUs from cart items (handles both database cart items and session cart dicts)
            product_skus = [
                item.product.sku if hasattr(item, 'product') else item['product'].sku 
                for item in cart_items
            ]
            if product_skus and recommendation_placement.strategy == 'association_rules':
                frequently_bought_together = get_product_recommendations(product_skus, top_n=3)
                annotate_products_with_promotions(frequently_bought_together)
        else:
            # If cart is empty, show popular products instead
            frequently_bought_together = get_product_recommendations([], top_n=3)
            annotate_products_with_promotions(frequently_bought_together)
    
    return render(request, 'storefront/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'using_db_cart': using_db_cart,
        'frequently_bought_together': frequently_bought_together,
        'recommendation_placement': recommendation_placement,
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
    
    # Redirect back to the appropriate page
    next_url = request.GET.get('next', 'storefront:product_detail')
    if next_url.startswith('http'):
        return redirect(next_url)
    elif ':' in next_url:
        from django.urls import reverse
        # Some named URLs (home, products, flash_sale_products, watchlist) take no SKU argument
        no_arg_views = {
            'storefront:home',
            'storefront:products',
            'storefront:flash_sale_products',
            'storefront:watchlist',
        }
        if next_url in no_arg_views:
            return redirect(reverse(next_url))
        else:
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
        no_arg_views = {
            'storefront:home',
            'storefront:products',
            'storefront:flash_sale_products',
            'storefront:watchlist',
        }
        if next_url in no_arg_views:
            return redirect(reverse(next_url))
        else:
            return redirect(reverse(next_url, args=[sku]))
    else:
        return redirect('storefront:watchlist')


# ============ CHAT FUNCTIONALITY ============

@login_required
def chat_create(request):
    """Create a new chat session"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to contact support.')
        return redirect('storefront:home')
    
    customer = request.user.customer_profile
    
    if request.method == 'POST':
        form = ChatForm(request.POST, customer=customer)
        message_form = ChatMessageForm(request.POST)
        
        if form.is_valid() and message_form.is_valid():
            # Create chat session
            chat_session = form.save(commit=False)
            chat_session.customer = customer
            chat_session.status = 'open'
            chat_session.save()
            
            # Create first message
            chat_message = message_form.save(commit=False)
            chat_message.session = chat_session
            chat_message.sender = 'customer'
            chat_message.save()
            
            messages.success(request, 'Your message has been sent. Our support team will respond soon.')
            return redirect('storefront:chat_detail', session_id=chat_session.id)
    else:
        form = ChatForm(customer=customer)
        message_form = ChatMessageForm()
    
    return render(request, 'storefront/chat_create.html', {
        'form': form,
        'message_form': message_form,
    })


@login_required
def chat_list(request):
    """List all chat sessions for the customer"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to view chat history.')
        return redirect('storefront:home')
    
    customer = request.user.customer_profile
    chat_sessions = (
        ChatSession.objects
        .filter(customer=customer)
        .select_related('order')
        .prefetch_related('messages')
        .order_by('-updated_at')
    )
    
    # Track how many NEW admin messages have arrived since the customer's last message
    # This avoids a forever-increasing counter without adding new DB fields.
    for session in chat_sessions:
        admin_messages = session.messages.filter(sender='admin')
        last_customer_msg = session.messages.filter(sender='customer').order_by('-created_at').first()
        
        if last_customer_msg:
            # Only count admin messages sent after the customer's last reply
            unread_admin_messages = admin_messages.filter(created_at__gt=last_customer_msg.created_at)
        else:
            # If the customer has never replied, treat all admin messages as "new"
            unread_admin_messages = admin_messages
        
        session.unread_count = unread_admin_messages.count()
    
    return render(request, 'storefront/chat_list.html', {
        'chat_sessions': chat_sessions,
    })


@login_required
def chat_detail(request, session_id):
    """View and send messages in a chat session"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to view chat details.')
        return redirect('storefront:home')
    
    customer = request.user.customer_profile
    chat_session = get_object_or_404(ChatSession, id=session_id, customer=customer)
    
    if request.method == 'POST':
        form = ChatMessageForm(request.POST)
        if form.is_valid():
            chat_message = form.save(commit=False)
            chat_message.session = chat_session
            chat_message.sender = 'customer'
            chat_message.save()
            
            # Update session updated_at
            chat_session.save()  # This will update updated_at due to auto_now
            
            messages.success(request, 'Message sent.')
            return redirect('storefront:chat_detail', session_id=session_id)
    else:
        form = ChatMessageForm()
    
    # Get all messages (use chat_messages to avoid conflict with Django messages)
    chat_messages = chat_session.messages.all().order_by('created_at')
    
    return render(request, 'storefront/chat_detail.html', {
        'chat_session': chat_session,
        'messages_list': chat_messages,
        'form': form,
    })


@login_required
def chat_close(request, session_id):
    """Close a chat session"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to close chat sessions.')
        return redirect('storefront:home')
    
    customer = request.user.customer_profile
    chat_session = get_object_or_404(ChatSession, id=session_id, customer=customer)
    
    if request.method == 'POST':
        chat_session.status = 'closed'
        chat_session.save()
        messages.success(request, 'Chat session closed.')
        return redirect('storefront:chat_list')
    
    return redirect('storefront:chat_detail', session_id=session_id)


def flash_sale_products(request):
    """Display all products on flash sale (both category-based and product-specific)"""
    today = date.today()
    
    # Get all active flash sale promotions (ending within 3 days)
    flash_sale_promotions = Promotion.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).prefetch_related('categories', 'products')
    
    # Collect all products on flash sale
    flash_sale_products_set = set()
    
    for promotion in flash_sale_promotions:
        days_remaining = (promotion.end_date - today).days
        if days_remaining <= 3:  # Flash sale (3 days or less)
            # Add products from category-based promotions
            for category in promotion.categories.all():
                category_products = Product.objects.filter(
                    category=category,
                    is_active=True,
                    archived=False,
                    stock__gte=0
                )
                flash_sale_products_set.update(category_products)
            
            # Add product-specific promotions
            for product in promotion.products.filter(is_active=True, archived=False, stock__gte=0):
                flash_sale_products_set.add(product)
    
    # Convert to list and annotate with promotion data
    flash_sale_products_list = list(flash_sale_products_set)
    flash_sale_products_list = annotate_products_with_promotions(flash_sale_products_list)
    
    # Sort by discount (highest first) and then by rating
    flash_sale_products_list.sort(
        key=lambda p: (
            -p.active_promotion.discount_percent if p.active_promotion else 0,
            -p.rating,
            -p.created_at.timestamp() if hasattr(p.created_at, 'timestamp') else 0
        ),
        reverse=True
    )
    
    # Pagination
    paginator = Paginator(flash_sale_products_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'flash_sale_count': len(flash_sale_products_list),
    }
    
    return render(request, 'storefront/flash_sale_products.html', context)

# Aurora Chatbot Integration
@login_required
def aurora_chatbot_view(request):
    """Render the Aurora chatbot interface"""
    if not hasattr(request.user, 'customer_profile'):
        messages.error(request, 'You must be a customer to use Aurora.')
        return redirect('storefront:home')

    customer = request.user.customer_profile

    # Use get_or_create to simplify finding or creating an active session
    session, created = AiChatSession.objects.get_or_create(customer=customer, is_active=True)

    return render(request, 'storefront/aurora.html', {
        "session": session,
    })

@login_required
def ask_aurora(request):
    """Handle user queries to the Aurora chatbot"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    session_id = request.POST.get('session_id')
    user_query = request.POST.get('message_content', '').strip()

    if not session_id or not user_query:
        return JsonResponse({'error': 'Session ID and message are required.'}, status=400)

    try:
        session = AiChatSession.objects.get(pk=session_id, customer=request.user.customer_profile)
    except AiChatSession.DoesNotExist:
        return JsonResponse({'error': 'Chat session not found.'}, status=404)

    # 1. Save the user's message
    user_message = AiChatMessage.objects.create(
        session=session,
        sender='user',
        content=user_query
    )

    # 2. Simulate a call to the Gemini/Aurora backend
    # In a real application, you would call your ML service here.
    # For now, we'll just provide a placeholder response.
    bot_response_content = f"Thank you for asking about '{user_query}'. I am still in training, but I am learning to answer your questions about products, orders, and more!"

    # 3. Save the bot's response
    bot_message = AiChatMessage.objects.create(
        session=session,
        sender='bot',
        content=bot_response_content
    )

    # 4. Return both messages to be rendered by the frontend
    return JsonResponse({
        'user_message': user_message.to_dict(),
        'bot_message': bot_message.to_dict(),
    })
