from decimal import Decimal

from django.db import models

from users.models import Customer

class Category(models.Model):
	"""Supports US001, US002, US003, US004 and ADM002 by structuring the product taxonomy."""
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=120, unique=True)
	description = models.TextField(blank=True)
	parent = models.ForeignKey(
		'self',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='children'
	)

	class Meta:
		verbose_name_plural = 'Categories'
		ordering = ['name']

	def __str__(self):
		return self.name
	
	def get_all_products(self):
		subcat_ids = self.children.values_list("id", flat=True)
		return Product.objects.filter(
			models.Q(category=self) | models.Q(category__in=subcat_ids),
			stock__gte=0,
			is_active=True,
			archived=False
		)

class Product(models.Model):
	"""Backs US001-US004 and ADM001-ADM004 with catalogue, pricing, rating, and inventory data."""
	sku = models.CharField(max_length=30, unique=True)
	name = models.CharField(max_length=150)
	description = models.TextField(blank=True)
	category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
	price = models.DecimalField(max_digits=10, decimal_places=2)
	rating = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('0.0'))
	stock = models.PositiveIntegerField(default=0)
	reorder_threshold = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	archived = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return f"{self.sku} - {self.name}"


class Order(models.Model):
	"""Delivers US005, US006, US012 and ADM010 order tracking across the purchase lifecycle."""
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('processing', 'Processing'),
		('shipped', 'Shipped'),
		('delivered', 'Delivered'),
		('cancelled', 'Cancelled'),
	]

	customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
	total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
	shipping_address = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Order #{self.pk} ({self.status})"


class OrderItem(models.Model):
	"""Captures line items for US005, US006, US012 and supports ADM010 fulfilment updates."""
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField(default=1)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2)

	def __str__(self):
		return f"{self.product.name} x {self.quantity}"


class Cart(models.Model):
	"""Enables US005 and US006 by holding an in-progress basket prior to checkout."""
	customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='cart')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Cart for {self.customer.user.username}"


class CartItem(models.Model):
	"""Stores per-product quantities for US005 and US006 within the active cart."""
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField(default=1)
	added_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.product.name} ({self.quantity})"


class Review(models.Model):
	"""Provides US004, US013 surfaceable feedback and ADM011 moderation workflows."""
	RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
	customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')
	rating = models.IntegerField(choices=RATING_CHOICES)
	title = models.CharField(max_length=100, blank=True)
	comment = models.TextField(blank=True)
	is_approved = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Review {self.rating}/5 for {self.product.name}"


class Promotion(models.Model):
	"""Targets US014 personalised offers while ADM012 schedules category-based campaigns."""
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
	start_date = models.DateField()
	end_date = models.DateField()
	categories = models.ManyToManyField(Category, blank=True, related_name='promotions')
	products = models.ManyToManyField('Product', blank=True, related_name='promotions')
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['-start_date']

	def __str__(self):
		return self.name
	
	def applies_to_product(self, product):
		"""Check if this promotion applies to a given product"""
		# Check product-specific first (higher priority)
		if self.products.filter(id=product.id).exists():
			return True
		# Check category-based
		if self.categories.filter(id=product.category.id).exists():
			return True
		return False


class Watchlist(models.Model):
	"""Implements US015 persistent watchlists for future purchasing decisions."""
	customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='watchlist')
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Watchlist for {self.customer.user.username}"


class WatchlistItem(models.Model):
	"""Stores the individual product selections supporting US015 watchlist management."""
	watchlist = models.ForeignKey(Watchlist, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.CASCADE)
	added_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('watchlist', 'product')

	def __str__(self):
		return f"{self.product.name} in watchlist"


class ChatSession(models.Model):
	"""Supports US016 shopper enquiries and ADM013 staff oversight of active conversations."""
	STATUS_CHOICES = [
		('open', 'Open'),
		('closed', 'Closed'),
	]

	customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='chat_sessions')
	order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')
	subject = models.CharField(max_length=150)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Chat with {self.customer.user.username} ({self.status})"


class ChatMessage(models.Model):
	"""Records conversation history for US016 dialogues and ADM013 review of responses."""
	SENDER_CHOICES = [
		('customer', 'Customer'),
		('admin', 'Admin'),
	]

	session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
	sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
	message = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"{self.sender} message"

# AI Chatbot
class AiChatSession(models.Model):
    # Links to the user
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ai_chat_sessions')
 
    # Metadata for sorting and display
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status for clearing/archiving
    is_active = models.BooleanField(default=True) 
    
    class Meta:
        # Show newest sessions first
        ordering = ['-updated_at']

    def total_tokens(self):
    	return self.messages.aggregate(total=models.Sum('token_usage'))['total'] or 0

class AiChatMessage(models.Model):
    session = models.ForeignKey(
        AiChatSession,
        on_delete=models.CASCADE,
        related_name='messages'  # Use this to fetch the messages for a session
    )

    SENDER_CHOICES = [
        ('user', 'User'),
        ('bot', 'Aurora Assistant'),
    ]

    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField(blank=True, null=True)
    token_usage = models.IntegerField(default=0)
    model_used = models.CharField(max_length=50, blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} message in session {self.session.id}"

    def serialize(self):
        return {
            'id': self.id,
            'session_id': self.session.id,
            'sender': self.sender,
            'content': self.content,
            'token_usage': self.token_usage,
            'model_used': self.model_used,
            'timestamp': self.timestamp.isoformat(),
        }

    class Meta:
        ordering = ['timestamp']
