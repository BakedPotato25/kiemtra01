from django.contrib import admin
from .models import BlogPost, CartItem, CompareItem, Order, OrderItem, SavedItem, Testimonial


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
	list_display = ("user", "product_name", "product_service", "quantity", "unit_price", "updated_at")
	list_filter = ("product_service",)
	search_fields = ("user__username", "product_name")


class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	readonly_fields = ("product_service", "product_id", "product_name", "product_brand", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "total_amount", "status", "created_at")
	list_filter = ("status",)
	search_fields = ("user__username", "id")
	inlines = [OrderItemInline]


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
	list_display = ("title", "category", "author", "published_at")
	search_fields = ("title", "category", "author", "slug")
	prepopulated_fields = {"slug": ("title",)}


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
	list_display = ("name", "role", "rating", "is_featured", "created_at")
	list_filter = ("is_featured", "rating")
	search_fields = ("name", "role", "quote")


@admin.register(SavedItem)
class SavedItemAdmin(admin.ModelAdmin):
	list_display = ("user", "product_name", "product_service", "unit_price", "created_at")
	list_filter = ("product_service",)
	search_fields = ("user__username", "product_name", "product_brand")


@admin.register(CompareItem)
class CompareItemAdmin(admin.ModelAdmin):
	list_display = ("user", "product_name", "product_service", "unit_price", "stock", "created_at")
	list_filter = ("product_service",)
	search_fields = ("user__username", "product_name", "product_brand")
