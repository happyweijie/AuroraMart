from django import forms
from .models import Review, ChatSession, ChatMessage, Order


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


class ReviewForm(forms.ModelForm):
    """Form for submitting product reviews"""
    
    rating = forms.IntegerField(
        widget=forms.HiddenInput(attrs={
            'id': 'rating-input',
        }),
        required=True
    )
    
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'Review Title (Optional)',
                'maxlength': '100'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'rows': 6,
                'placeholder': 'Share your experience with this product...',
                'required': True,
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].required = True
        self.fields['comment'].required = True
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is not None:
            rating = int(rating)  # Convert choice to integer
            if rating < 1 or rating > 5:
                raise forms.ValidationError('Rating must be between 1 and 5.')
        return rating


class ChatForm(forms.ModelForm):
    """Form for submitting customer support chat messages"""
    
    class Meta:
        model = ChatSession
        fields = ['subject', 'order']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'placeholder': 'What can we help you with?',
                'required': True,
            }),
            'order': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.customer = kwargs.pop('customer', None)
        super().__init__(*args, **kwargs)
        if self.customer:
            # Only show orders for this customer
            self.fields['order'].queryset = Order.objects.filter(
                customer=self.customer
            ).order_by('-created_at')
            self.fields['order'].required = False
            self.fields['order'].empty_label = 'Not related to an order'


class ChatMessageForm(forms.ModelForm):
    """Form for sending messages in a chat session"""
    
    class Meta:
        model = ChatMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
                'rows': 4,
                'placeholder': 'Type your message...',
                'required': True,
            }),
        }
