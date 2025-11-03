from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class User(AbstractUser):
    # use signals to update 
    is_customer = models.BooleanField(default=False)
    is_admin_user = models.BooleanField(default=False)


class Customer(models.Model):
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
    ]

    EMPLOYMENT_CHOICES = [
        ("Full-Time", "Full-Time"),
        ("Part-Time", "Part-Time"),
        ("Self-Employed", "Self-Employed"),
        ("Student", "Student"),
        ("Retired", "Retired"),
    ]

    OCCUPATION_CHOICES = [
        ('Admin', 'Admin'),
        ('Education', 'Education'),
        ('Sales', 'Sales'),
        ('Service', 'Service'),
        ('Skilled Trades', 'Skilled Trades'),
        ('Tech', 'Tech'),
    ]

    EDUCATION_CHOICES = [
        ('Secondary', 'Secondary'),
        ('Diploma', 'Diploma'),
        ('Bachelor', 'Bachelor'),
        ('Master', 'Master'),
        ('Doctorate', 'Doctorate'),
    ]

    CATEGORY_CHOICES = [
        ('Electronics', 'Electronics'),
        ('Fashion - Men', 'Fashion - Men'),
        ('Fashion - Women', 'Fashion - Women'),
        ('Home & Kitchen', 'Home & Kitchen'),
        ('Beauty & Personal Care', 'Beauty & Personal Care'),
        ('Sports & Outdoors', 'Sports & Outdoors'),
        ('Books', 'Books'),
        ('Groceries & Gourmet', 'Groceries & Gourmet'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_profile")
    age = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(99)])
    household_size = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    has_children = models.BooleanField()
    monthly_income_sgd = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    employment_status = models.CharField(max_length=30, choices=EMPLOYMENT_CHOICES)
    occupation = models.CharField(max_length=100, choices=OCCUPATION_CHOICES)
    education = models.CharField(max_length=30, choices=EDUCATION_CHOICES)
    preferred_category = models.CharField(max_length=100, blank=True, null=True, choices=CATEGORY_CHOICES)


class AdminProfile(models.Model):
    """
    Admin or staff users who manage product catalogues and customer records.
    """
    POSITION_CHOICES = [
        ('Manager', 'Manager'),
        ('Supervisor', 'Supervisor'),
        ('Staff', 'Staff'),
    ]

    DEPARTMENT_CHOICES = [
        ('Product Management', 'Product Management'),
        ('Customer Service', 'Customer Service'),
        ('Sales', 'Sales'),
        ('Marketing', 'Marketing'),
        ('IT Support', 'IT Support'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    position = models.CharField(max_length=100, blank=True, null=True, choices=POSITION_CHOICES)
    department = models.CharField(max_length=100, blank=True, null=True, choices=DEPARTMENT_CHOICES)

    def __str__(self):
        return f"Admin: {self.user.username}"
    