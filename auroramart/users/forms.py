from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Customer

class CustomerRegistrationForm(UserCreationForm):
    # User fields
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    
    # Customer profile fields
    age = forms.IntegerField(min_value=1, max_value=99, required=True)
    household_size = forms.IntegerField(min_value=1, required=True)
    has_children = forms.BooleanField(required=False)
    monthly_income_sgd = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=True)
    gender = forms.ChoiceField(choices=Customer.GENDER_CHOICES, required=True)
    employment_status = forms.ChoiceField(choices=Customer.EMPLOYMENT_CHOICES, required=True)
    occupation = forms.ChoiceField(choices=Customer.OCCUPATION_CHOICES, required=True)
    education = forms.ChoiceField(choices=Customer.EDUCATION_CHOICES, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 
                  'password2', 'age', 'household_size', 'monthly_income_sgd']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind classes to all fields
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'w-4 h-4 text-cyan border-gray-300 rounded focus:ring-cyan'
            else:
                field.widget.attrs['class'] = 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent'
            field.widget.attrs['placeholder'] = field.label
        
        # Define specific placeholders
        self.fields['email'].widget.attrs['placeholder'] = 'Email'
        self.fields['first_name'].widget.attrs['placeholder'] = 'First Name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Last Name'
        self.fields['password1'].widget.attrs['placeholder'] = 'Enter your password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm your password'
        self.fields['age'].widget.attrs['placeholder'] = 'Age'
        self.fields['household_size'].widget.attrs['placeholder'] = 'Household Size'
        self.fields['monthly_income_sgd'].widget.attrs['placeholder'] = 'Monthly Income'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Create customer profile
            Customer.objects.create(
                user=user,
                age=self.cleaned_data['age'],
                household_size=self.cleaned_data['household_size'],
                has_children=self.cleaned_data['has_children'],
                monthly_income_sgd=self.cleaned_data['monthly_income_sgd'],
                gender=self.cleaned_data['gender'],
                employment_status=self.cleaned_data['employment_status'],
                occupation=self.cleaned_data['occupation'],
                education=self.cleaned_data['education'],
            )
        
        return user


class CustomerLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent',
            'placeholder': 'Password'
        })
    )