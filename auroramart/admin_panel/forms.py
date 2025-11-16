from django import forms
from django.contrib.auth.forms import UserCreationForm
from storefront.models import Product, Category, Order, Promotion
from users.models import Customer, User
from decimal import Decimal


class ProductForm(forms.ModelForm):
    """Form for creating and editing products
    
    Note: Rating is excluded as it should be calculated from customer reviews,
    not manually edited by admins.
    """
    
    class Meta:
        model = Product
        fields = ['sku', 'name', 'description', 'category', 'price', 
                  'stock', 'reorder_threshold', 'is_active', 'archived']
        widgets = {
            'sku': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'SKU (e.g., PROD-001)'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'Product Name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'rows': 4,
                'placeholder': 'Product Description'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'min': '0',
                'placeholder': '0'
            }),
            'reorder_threshold': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'min': '0',
                'placeholder': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan border-gray-300 rounded focus:ring-cyan'
            }),
            'archived': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan border-gray-300 rounded focus:ring-cyan'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
    
    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if sku:
            # Check if SKU already exists (excluding current instance)
            existing = Product.objects.filter(sku=sku)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError('A product with this SKU already exists.')
        return sku
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price
    
    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise forms.ValidationError('Stock cannot be negative.')
        return stock


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories"""
    
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'Category Name'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'category-slug'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'rows': 3,
                'placeholder': 'Category Description'
            }),
            'parent': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude self from parent choices to prevent circular references
        if self.instance.pk:
            self.fields['parent'].queryset = Category.objects.exclude(pk=self.instance.pk).order_by('name')
        else:
            self.fields['parent'].queryset = Category.objects.all().order_by('name')
        self.fields['parent'].required = False


class BulkInventoryUpdateForm(forms.Form):
    """Form for bulk updating inventory levels"""
    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'space-y-2'
        }),
        required=False
    )
    stock_adjustment = forms.IntegerField(
        help_text='Enter positive number to add stock, negative to subtract',
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            'placeholder': '0'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['products'].queryset = Product.objects.filter(archived=False).order_by('name')


class CustomerForm(forms.ModelForm):
    """Form for editing customer demographics"""
    
    class Meta:
        model = Customer
        # Preferred category is ML-driven; admins shouldn't edit it directly here.
        fields = ['age', 'household_size', 'has_children', 'monthly_income_sgd',
                  'gender', 'employment_status', 'occupation', 'education']
        widgets = {
            'age': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'min': '1',
                'max': '99'
            }),
            'household_size': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'min': '1'
            }),
            'has_children': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan border-gray-300 rounded focus:ring-cyan'
            }),
            'monthly_income_sgd': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'step': '0.01',
                'min': '0'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
            }),
            'employment_status': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
            }),
            'occupation': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
            }),
            'education': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
            }),
        }


class OrderStatusUpdateForm(forms.Form):
    """Form for updating order status"""
    status = forms.ChoiceField(
        choices=Order.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
        })
    )


class PromotionForm(forms.ModelForm):
    """Form for creating and editing promotions"""
    
    class Meta:
        model = Promotion
        fields = ['name', 'description', 'discount_percent', 'start_date', 
                  'end_date', 'categories', 'products', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'Promotion Name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'rows': 4,
                'placeholder': 'Promotion Description'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0.00'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'type': 'date'
            }),
            'categories': forms.SelectMultiple(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'size': '5'
            }),
            'products': forms.SelectMultiple(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'size': '5'
            }),
            'preferred_category': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'Optional: Preferred category slug'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan border-gray-300 rounded focus:ring-cyan'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show categories that have active products (matching storefront filter)
        self.fields['categories'].queryset = Category.objects.filter(
            products__is_active=True,
            products__archived=False,
            products__stock__gte=0
        ).distinct().order_by('name')
        self.fields['categories'].required = False
        
        self.fields['products'].queryset = Product.objects.filter(
            archived=False, is_active=True
        ).select_related('category').order_by('name')
        self.fields['products'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        categories = cleaned_data.get('categories')
        products = cleaned_data.get('products')
        
        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError('End date must be after start date.')
        
        # Validate that at least categories OR products are selected
        if not categories and not products:
            raise forms.ValidationError('You must select at least one category or product for the promotion to apply.')
        
        return cleaned_data
    
    def clean_discount_percent(self):
        discount = self.cleaned_data.get('discount_percent')
        if discount is not None:
            if discount < 0 or discount > 100:
                raise forms.ValidationError('Discount must be between 0 and 100.')
        return discount


class AdminUserForm(forms.ModelForm):
    """Form for creating and editing admin users"""
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            'placeholder': 'Leave blank to keep existing password'
        }),
        help_text='Leave blank to keep existing password'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'email@example.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'Last Name'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan border-gray-300 rounded focus:ring-cyan'
            }),
            'is_superuser': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan border-gray-300 rounded focus:ring-cyan'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-cyan border-gray-300 rounded focus:ring-cyan'
            }),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class AdminUserCreateForm(UserCreationForm):
    """Form for creating new admin users"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    is_staff = forms.BooleanField(required=False, initial=True)
    is_superuser = forms.BooleanField(required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_superuser']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            }),
        }

