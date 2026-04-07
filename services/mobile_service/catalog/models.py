from django.db import models


class Product(models.Model):
	name = models.CharField(max_length=255)
	brand = models.CharField(max_length=120, default="Generic")
	description = models.TextField(blank=True)
	image_url = models.URLField(blank=True)
	price = models.DecimalField(max_digits=12, decimal_places=2)
	stock = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-updated_at"]

	def __str__(self):
		return self.name
