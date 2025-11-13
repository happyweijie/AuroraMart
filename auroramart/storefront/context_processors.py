from django.db.models import Count
from .models import Category, Product


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

