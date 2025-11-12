from django.urls import path
from . import views

app_name = 'storefront'

urlpatterns = [
    path('', views.index, name='home'),
    path('products/', views.index, name='products'),
    path('category/<slug:category>/', views.index, name='category'),
    path('cart/', views.index, name='cart'),
    path('watchlist/', views.index, name='watchlist'),
    path('products/<str:sku>/', views.index, name='product_detail'),
]