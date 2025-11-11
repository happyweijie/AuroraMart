from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    # Placeholder URLs for other admin views
    path('products/', views.dashboard, name='products'),
    path('categories/', views.dashboard, name='categories'),
    path('inventory/', views.dashboard, name='inventory'),
    path('pricing/', views.dashboard, name='pricing'),
    path('customers/', views.dashboard, name='customers'),
    path('orders/', views.dashboard, name='orders'),
    path('reviews/', views.dashboard, name='reviews'),
    path('promotions/', views.dashboard, name='promotions'),
    path('chat/', views.dashboard, name='chat'),
    path('import-export/', views.dashboard, name='import_export'),
    path('recommendations/', views.dashboard, name='recommendations'),
    path('preferred-category/', views.dashboard, name='preferred_category'),
    path('audit/', views.dashboard, name='audit'),
    path('admin-users/', views.dashboard, name='admin_users'),
]
