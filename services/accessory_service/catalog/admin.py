from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
	list_display = ("id", "name", "brand", "price", "stock", "updated_at")
	search_fields = ("name", "brand")
