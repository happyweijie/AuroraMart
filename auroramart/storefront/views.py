from django.shortcuts import render
from django.http import HttpResponse
from .models import Product

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
