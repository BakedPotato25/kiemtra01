from decimal import Decimal, InvalidOperation

from django.db.models import Q
from rest_framework import viewsets

from .models import Product
from .permissions import StaffWritePermission
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
	serializer_class = ProductSerializer
	permission_classes = [StaffWritePermission]

	def get_queryset(self):
		queryset = Product.objects.all()
		search = (self.request.query_params.get("search") or "").strip()
		brand = (self.request.query_params.get("brand") or "").strip()
		min_price = self.request.query_params.get("min_price")
		max_price = self.request.query_params.get("max_price")
		in_stock = (self.request.query_params.get("in_stock") or "").lower()

		if search:
			queryset = queryset.filter(
				Q(name__icontains=search) | Q(description__icontains=search) | Q(brand__icontains=search)
			)

		if brand:
			queryset = queryset.filter(brand__icontains=brand)

		if min_price is not None and min_price != "":
			try:
				queryset = queryset.filter(price__gte=Decimal(min_price))
			except (InvalidOperation, ValueError):
				pass

		if max_price is not None and max_price != "":
			try:
				queryset = queryset.filter(price__lte=Decimal(max_price))
			except (InvalidOperation, ValueError):
				pass

		if in_stock in {"1", "true", "yes", "on"}:
			queryset = queryset.filter(stock__gt=0)

		return queryset
