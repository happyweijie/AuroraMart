from django.db.models import Count
from .models import Category, Product, Cart


def categories_with_products(request):
    """
    Context processor to make categories with products available in all templates.
    Returns top 10 categories that have active products.
    """
    categories = Category.objects.filter(
        products__is_active=True,
        products__archived=False,
        products__stock__gte=0
    ).annotate(
        product_count=Count('products')
    ).distinct().order_by('-product_count', 'name')[:10]
    
    return {
        'nav_categories': categories
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

