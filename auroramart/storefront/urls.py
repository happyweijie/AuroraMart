from django.urls import path
from . import views

app_name = 'storefront'

urlpatterns = [
    path('', views.index, name='home'),
    path('products/', views.products, name='products'),
    path('products/<str:sku>/', views.product_detail, name='product_detail'),
    path('category/<str:slug>/', views.category, name='category'),
    path('cart/', views.index, name='cart'),
    path('watchlist/', views.index, name='watchlist'),
]