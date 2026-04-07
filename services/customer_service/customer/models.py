from django.conf import settings
from django.db import models


class CartItem(models.Model):
	SERVICE_LAPTOP = "laptop"
	SERVICE_MOBILE = "mobile"
	SERVICE_ACCESSORY = "accessory"
	SERVICE_CHOICES = [
		(SERVICE_LAPTOP, "Laptop"),
		(SERVICE_MOBILE, "Mobile"),
		(SERVICE_ACCESSORY, "Accessory"),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
	product_service = models.CharField(max_length=20, choices=SERVICE_CHOICES)
	product_id = models.PositiveIntegerField()
	product_name = models.CharField(max_length=255)
	product_brand = models.CharField(max_length=120, blank=True)
	product_image_url = models.URLField(blank=True)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)
	quantity = models.PositiveIntegerField(default=1)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ("user", "product_service", "product_id")
		ordering = ["-updated_at"]

	@property
	def total_price(self):
		return self.unit_price * self.quantity

	def __str__(self):
		return f"{self.user.username} - {self.product_name} ({self.quantity})"


class Order(models.Model):
	STATUS_PENDING = "pending"
	STATUS_PAID = "paid"
	STATUS_CANCELLED = "cancelled"
	STATUS_CHOICES = [
		(STATUS_PENDING, "Pending"),
		(STATUS_PAID, "Paid"),
		(STATUS_CANCELLED, "Cancelled"),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
	total_amount = models.DecimalField(max_digits=12, decimal_places=2)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return f"Order #{self.id} - {self.user.username}"


class OrderItem(models.Model):
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
	product_service = models.CharField(max_length=20, choices=CartItem.SERVICE_CHOICES)
	product_id = models.PositiveIntegerField()
	product_name = models.CharField(max_length=255)
	product_brand = models.CharField(max_length=120, blank=True)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)
	quantity = models.PositiveIntegerField()

	@property
	def total_price(self):
		return self.unit_price * self.quantity

	def __str__(self):
		return f"{self.product_name} x{self.quantity}"


class BlogPost(models.Model):
	title = models.CharField(max_length=220)
	slug = models.SlugField(unique=True)
	category = models.CharField(max_length=80)
	author = models.CharField(max_length=120)
	excerpt = models.TextField()
	body = models.TextField()
	hero_image_url = models.URLField(blank=True)
	published_at = models.DateField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-published_at", "-id"]

	def __str__(self):
		return self.title


class Testimonial(models.Model):
	name = models.CharField(max_length=120)
	role = models.CharField(max_length=120)
	rating = models.PositiveSmallIntegerField(default=5)
	quote = models.TextField()
	avatar_url = models.URLField(blank=True)
	is_featured = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	@property
	def stars(self):
		value = max(1, min(5, int(self.rating or 0)))
		return "*" * value

	def __str__(self):
		return f"{self.name} ({self.role})"


class SavedItem(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_items")
	product_service = models.CharField(max_length=20, choices=CartItem.SERVICE_CHOICES)
	product_id = models.PositiveIntegerField()
	product_name = models.CharField(max_length=255)
	product_brand = models.CharField(max_length=120, blank=True)
	product_image_url = models.URLField(blank=True)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ("user", "product_service", "product_id")
		ordering = ["-created_at"]

	def __str__(self):
		return f"Saved: {self.product_name} by {self.user.username}"


class CompareItem(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="compare_items")
	product_service = models.CharField(max_length=20, choices=CartItem.SERVICE_CHOICES)
	product_id = models.PositiveIntegerField()
	product_name = models.CharField(max_length=255)
	product_brand = models.CharField(max_length=120, blank=True)
	product_image_url = models.URLField(blank=True)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)
	stock = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ("user", "product_service", "product_id")
		ordering = ["-created_at"]

	def __str__(self):
		return f"Compare: {self.product_name} by {self.user.username}"
