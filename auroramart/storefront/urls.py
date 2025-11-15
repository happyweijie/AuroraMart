from django.urls import path
from . import views

app_name = 'storefront'

urlpatterns = [
    path('', views.index, name='home'),
    path('products/', views.products, name='products'),
    path('products/<str:sku>/', views.product_detail, name='product_detail'),
    path('category/<str:slug>/', views.category, name='category'),
    
    # Cart URLs
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<str:sku>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart'),
    path('cart/update/', views.update_cart_item, name='update_cart_session'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart_session'),
    
    # Checkout & Orders URLs
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/<int:order_id>/confirmation/', views.order_confirmation_view, name='order_confirmation'),
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
    path('orders/<int:order_id>/cancel/', views.cancel_order_view, name='cancel_order'),
    
    # Reviews
    path('products/<str:sku>/review/', views.review_create_view, name='review_create'),
    path('reviews/', views.review_list_view, name='review_list'),
    
    # Watchlist (placeholder)
    path('watchlist/', views.index, name='watchlist'),
]