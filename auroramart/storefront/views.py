from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count, Q
from .models import Product, Category

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
