from django.shortcuts import render
from django.core.paginator import Paginator
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

    return render(request, 'storefront/home.html', {
        'featured_products': products
        })

def products(request):
    # Get the sort parameter
    sort_by = request.GET.get('sort', 'rating')
    
    # Base queryset
    products = Product.objects.filter(
        stock__gte=0,
        is_active=True,
        archived=False
    )
    
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

    return render(request, 'storefront/products.html', {
        'page_obj': page_obj,
    })

def category(request, slug):    
    # Get the sort parameter
    sort_by = request.GET.get('sort', 'rating')
    
    # Get category object
    category_obj = Category.objects.get(slug=slug)
    
    # Base queryset
    products = category_obj.products.filter(
        stock__gte=0,
        is_active=True,
        archived=False
    )
    
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
    })
