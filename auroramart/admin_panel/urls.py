from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # Protected admin views
    path('products/', views.product_list, name='products'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<str:sku>/edit/', views.product_update, name='product_update'),
    path('products/<str:sku>/delete/', views.product_delete, name='product_delete'),
    path('categories/', views.category_list, name='categories'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_update, name='category_update'),
    path('inventory/', views.inventory_management, name='inventory'),
    path('pricing/', views.pricing_management, name='pricing'),
    path('customers/', views.customer_list, name='customers'),
    path('customers/<int:customer_id>/edit/', views.customer_update, name='customer_update'),
    path('orders/', views.admin_order_list, name='orders'),
    path('orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('reviews/', views.review_management, name='reviews'),
    path('reviews/<int:review_id>/approve/', views.review_approve, name='review_approve'),
    path('reviews/<int:review_id>/reject/', views.review_reject, name='review_reject'),
    path('promotions/', views.promotion_management, name='promotions'),
    path('chat/', views.chat_support, name='chat'),
    path('import-export/', views.import_export, name='import_export'),
    path('recommendations/', views.recommendation_placement_list, name='recommendations'),
    path('preferred-category/', views.preferred_category_analysis, name='preferred_category'),
    path('audit/', views.audit_log, name='audit'),
    path('admin-users/', views.admin_user_management, name='admin_users'),
]
