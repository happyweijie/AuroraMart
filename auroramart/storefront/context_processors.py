from django.db.models import Count
from datetime import date
from .models import Category, Product, Cart, Watchlist, Promotion


def categories_with_products(request):
    """
    Context processor to make categories with products available in all templates.
    Returns top 10 categories that have active products.
    Annotates categories with flash sale information.
    """
    today = date.today()
    
    # Get all active flash sales (ending within 3 days)
    flash_sale_promotions = Promotion.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).prefetch_related('categories', 'products')
    
    # Find categories with flash sales
    flash_sale_categories = set()
    flash_sale_data = {}  # category_id -> {promotion, end_date}
    
    # Collect ALL active flash sales (for banner display)
    active_flash_sales = []  # List of all flash sale promotions
    
    for promotion in flash_sale_promotions:
        days_remaining = (promotion.end_date - today).days
        if days_remaining <= 3:  # Flash sale (3 days or less)
            # Add to active flash sales list
            active_flash_sales.append({
                'promotion': promotion,
                'end_date': promotion.end_date,
                'discount': promotion.discount_percent,
                'days_remaining': days_remaining
            })
            
            # Process category-based promotions
            for category in promotion.categories.all():
                flash_sale_categories.add(category.id)
                # Keep the promotion with the highest discount or shortest time remaining
                if category.id not in flash_sale_data or days_remaining < (flash_sale_data[category.id]['end_date'] - today).days:
                    flash_sale_data[category.id] = {
                        'promotion': promotion,
                        'end_date': promotion.end_date,
                        'discount': promotion.discount_percent
                    }
    
    categories = Category.objects.filter(
        products__is_active=True,
        products__archived=False,
        products__stock__gte=0
    ).annotate(
        product_count=Count('products')
    ).distinct().order_by('-product_count', 'name')[:10]
    
    # Annotate categories with flash sale data
    for category in categories:
        if category.id in flash_sale_categories:
            category.has_flash_sale = True
            category.flash_sale_promotion = flash_sale_data[category.id]['promotion']
            category.flash_sale_end_date = flash_sale_data[category.id]['end_date']
            category.flash_sale_discount = flash_sale_data[category.id]['discount']
        else:
            category.has_flash_sale = False
            category.flash_sale_promotion = None
            category.flash_sale_end_date = None
            category.flash_sale_discount = None
    
    # Get current category slug from URL if available
    current_category_slug = None
    if hasattr(request, 'resolver_match') and request.resolver_match:
        kwargs = request.resolver_match.kwargs
        # Check if we're on a category page (slug in URL kwargs)
        if 'slug' in kwargs:
            current_category_slug = kwargs['slug']
        # Check if we're on products page with category filter (from GET parameter)
        elif request.GET.get('category'):
            current_category_slug = request.GET.get('category')
    
    return {
        'nav_categories': categories,
        'current_category_slug': current_category_slug,
        'active_flash_sales': active_flash_sales  # All active flash sale promotions
    }


def cart_count(request):
    """
    Context processor to provide cart item count for badge in navigation.
    Works for both authenticated users (database) and guest users (session).
    """
    count = 0
    
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        # Count items in database cart
        try:
            cart = Cart.objects.get(customer=request.user.customer_profile)
            count = cart.items.count()
        except Cart.DoesNotExist:
            count = 0
    else:
        # Count items in session cart
        session_cart = request.session.get('cart', {})
        count = len(session_cart)
    
    return {
        'cart_item_count': count
    }


def watchlist_count(request):
    """
    Context processor to provide watchlist item count for badge in navigation.
    Only works for authenticated users with customer profiles.
    """
    count = 0
    
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        try:
            watchlist = Watchlist.objects.get(customer=request.user.customer_profile)
            count = watchlist.items.count()
        except Watchlist.DoesNotExist:
            count = 0
    
    return {
        'watchlist_count': count
    }

