from django import forms


class CheckoutForm(forms.Form):
    """Form for collecting shipping and payment information during checkout"""
    
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
    ]
    
    # Shipping Address Fields
    street_address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            'placeholder': 'Street address'
        })
    )
    
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            'placeholder': 'City'
        })
    )
    
    postal_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            'placeholder': 'Postal code'
        })
    )
    
    country = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            'placeholder': 'Country'
        })
    )
    
    # Payment Method (placeholder)
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
        })
    )
    
    def get_formatted_address(self):
        """Returns the formatted shipping address"""
        return f"{self.cleaned_data['street_address']}, {self.cleaned_data['city']}, {self.cleaned_data['postal_code']}, {self.cleaned_data['country']}"
