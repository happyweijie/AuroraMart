from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # Protected admin views
    path('products/', views.product_management, name='products'),
    path('categories/', views.category_management, name='categories'),
    path('inventory/', views.inventory_management, name='inventory'),
    path('pricing/', views.pricing_management, name='pricing'),
    path('customers/', views.customer_records, name='customers'),
    path('orders/', views.order_management, name='orders'),
    path('reviews/', views.review_management, name='reviews'),
    path('promotions/', views.promotion_management, name='promotions'),
    path('chat/', views.chat_support, name='chat'),
    path('import-export/', views.import_export, name='import_export'),
    path('recommendations/', views.recommendation_management, name='recommendations'),
    path('preferred-category/', views.preferred_category_analysis, name='preferred_category'),
    path('audit/', views.audit_log, name='audit'),
    path('admin-users/', views.admin_user_management, name='admin_users'),
]
