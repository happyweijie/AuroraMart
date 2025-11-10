from django.contrib import admin

from .models import (
	Category,
	Product,
	Order,
	OrderItem,
	Cart,
	CartItem,
	Review,
	Promotion,
	Watchlist,
	WatchlistItem,
	ChatSession,
	ChatMessage,
)


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0


class OrderAdmin(admin.ModelAdmin):
	list_display = ("id", "customer", "status", "total_price", "created_at")
	list_filter = ("status",)
	search_fields = ("customer__user__username",)
	inlines = (OrderItemInline,)


class CartItemInline(admin.TabularInline):
	model = CartItem
	extra = 0


class CartAdmin(admin.ModelAdmin):
	list_display = ("customer", "created_at")
	inlines = (CartItemInline,)


class CategoryAdmin(admin.ModelAdmin):
	list_display = ("name", "slug", "parent")
	search_fields = ("name", "slug")


class ProductAdmin(admin.ModelAdmin):
	list_display = ("sku", "name", "price", "stock", "is_active", "archived")
	list_filter = ("is_active", "archived", "category")
	search_fields = ("sku", "name")


class ReviewAdmin(admin.ModelAdmin):
	list_display = ("product", "customer", "rating", "is_approved", "created_at")
	list_filter = ("is_approved", "rating")
	search_fields = ("product__name", "customer__user__username")


class PromotionAdmin(admin.ModelAdmin):
	list_display = ("name", "discount_percent", "start_date", "end_date", "is_active")
	list_filter = ("is_active",)
	search_fields = ("name",)


class WatchlistItemInline(admin.TabularInline):
	model = WatchlistItem
	extra = 0


class WatchlistAdmin(admin.ModelAdmin):
	list_display = ("customer", "created_at")
	inlines = (WatchlistItemInline,)


class ChatMessageInline(admin.TabularInline):
	model = ChatMessage
	extra = 0


class ChatSessionAdmin(admin.ModelAdmin):
	list_display = ("customer", "order", "status", "created_at")
	list_filter = ("status",)
	inlines = (ChatMessageInline,)


# Register models with their ModelAdmin where helpful
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Promotion, PromotionAdmin)
admin.site.register(Watchlist, WatchlistAdmin)
admin.site.register(WatchlistItem)
admin.site.register(ChatSession, ChatSessionAdmin)
admin.site.register(ChatMessage)
