import os
import time
from copy import deepcopy
from decimal import Decimal, InvalidOperation

import requests
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CreateItemForm, DeleteItemForm, StaffLoginForm, StaffRegisterForm, UpdateItemForm

User = get_user_model()
SUPPORTED_SERVICES = ("laptop", "mobile", "accessory")
CUSTOMER_ANALYTICS_TTL_SECONDS = 25
_CUSTOMER_ANALYTICS_CACHE = {}


def _is_staff_user(user):
	return user.is_authenticated and user.is_staff


def _service_url(service_name):
	if service_name == "accessory":
		return os.getenv("ACCESSORY_SERVICE_URL", "http://accessory-service:8000")
	if service_name == "mobile":
		return os.getenv("MOBILE_SERVICE_URL", "http://mobile-service:8000")
	return os.getenv("LAPTOP_SERVICE_URL", "http://laptop-service:8000")


def _customer_service_url():
	return os.getenv("CUSTOMER_SERVICE_URL", "http://customer-service:8000")


def _empty_customer_analytics():
	return {
		"customer_count": 0,
		"active_customers": 0,
		"range_days": 30,
		"range_start": "",
		"range_end": "",
		"order_stats": {
			"total_orders": 0,
			"paid_orders": 0,
			"pending_orders": 0,
			"cancelled_orders": 0,
			"total_revenue": "0.00",
			"total_units_sold": 0,
			"average_paid_order_value": "0.00",
		},
		"top_customers": [],
		"customer_rows": [],
		"recent_orders": [],
		"revenue_trend_daily": [],
		"revenue_trend_weekly": [],
	}


def _resolve_range_days(raw_value):
	value = _to_int(raw_value)
	if value in {7, 30, 90}:
		return value
	return 30


def _build_trend_rows(series):
	rows = []
	max_value = Decimal("0")
	for point in series or []:
		value = _to_decimal(point.get("revenue"))
		if value > max_value:
			max_value = value

	for point in series or []:
		value = _to_decimal(point.get("revenue"))
		pct = int(round((value / max_value) * 100)) if max_value > 0 else 0
		rows.append(
			{
				"label": point.get("label") or "N/A",
				"revenue": f"{value:.2f}",
				"pct": pct,
			}
		)
	return rows


def _fetch_customer_analytics(customer_limit=200, recent_limit=20, range_days=30):
	range_days = _resolve_range_days(range_days)
	cache_key = (int(customer_limit), int(recent_limit), int(range_days))
	now = time.time()
	cached = _CUSTOMER_ANALYTICS_CACHE.get(cache_key)
	if cached and now - cached["ts"] <= CUSTOMER_ANALYTICS_TTL_SECONDS:
		return deepcopy(cached["data"])

	headers = {"X-Staff-Key": os.getenv("STAFF_API_KEY", "dev-staff-key")}
	endpoint = f"{_customer_service_url().rstrip('/')}/customer/staff/analytics/"
	try:
		response = requests.get(
			endpoint,
			headers=headers,
			params={
				"customer_limit": customer_limit,
				"recent_limit": recent_limit,
				"range_days": range_days,
			},
			timeout=8,
		)
		response.raise_for_status()
		payload = response.json()
		if isinstance(payload, dict):
			_CUSTOMER_ANALYTICS_CACHE[cache_key] = {"ts": now, "data": payload}
			return deepcopy(payload)
	except (requests.RequestException, ValueError):
		if cached:
			return deepcopy(cached["data"])
		return _empty_customer_analytics()

	return _empty_customer_analytics()


def _fetch_items(service_name):
	base_url = _service_url(service_name)
	try:
		response = requests.get(f"{base_url}/api/products/", timeout=5)
		response.raise_for_status()
		payload = response.json()
	except requests.RequestException:
		return []

	if isinstance(payload, dict) and "results" in payload:
		return payload["results"]
	if isinstance(payload, list):
		return payload
	return []


def _resolve_service_filter(raw_value):
	value = (raw_value or "").strip().lower()
	if value in {"all", *SUPPORTED_SERVICES}:
		return value
	return "all"


def _normalize_item(service_name, item):
	return {
		"service": service_name,
		"id": item.get("id"),
		"name": item.get("name", "N/A"),
		"brand": item.get("brand", ""),
		"description": item.get("description", ""),
		"image_url": item.get("image_url", ""),
		"price": item.get("price", "0"),
		"stock": item.get("stock", 0),
	}


def _fetch_dashboard_items(service_filter):
	services = SUPPORTED_SERVICES if service_filter == "all" else (service_filter,)
	items = []
	for service_name in services:
		for raw_item in _fetch_items(service_name):
			items.append(_normalize_item(service_name, raw_item))

	def _sort_key(item):
		try:
			item_id = int(item.get("id") or 0)
		except (TypeError, ValueError):
			item_id = 0
		return (item_id, item.get("service") or "")

	items.sort(key=_sort_key, reverse=True)
	return items


def _to_int(value):
	try:
		return int(value)
	except (TypeError, ValueError):
		return 0


def _to_decimal(value):
	try:
		return Decimal(str(value))
	except (InvalidOperation, TypeError, ValueError):
		return Decimal("0")


def _build_dashboard_stats():
	items = _fetch_dashboard_items("all")
	service_stats = {service_name: {"count": 0, "stock": 0} for service_name in SUPPORTED_SERVICES}
	total_stock = 0
	total_value = Decimal("0")
	low_stock_items = 0

	for item in items:
		service_name = item.get("service")
		stock = _to_int(item.get("stock"))
		price = _to_decimal(item.get("price"))

		total_stock += stock
		total_value += price * Decimal(stock)
		if stock <= 5:
			low_stock_items += 1

		if service_name in service_stats:
			service_stats[service_name]["count"] += 1
			service_stats[service_name]["stock"] += stock

	recent_items = items[:8]
	service_breakdown = []
	for service_name in SUPPORTED_SERVICES:
		service_breakdown.append(
			{
				"service": service_name,
				"count": service_stats[service_name]["count"],
				"stock": service_stats[service_name]["stock"],
			}
		)

	max_service_count = max([row["count"] for row in service_breakdown] or [1])
	max_service_stock = max([row["stock"] for row in service_breakdown] or [1])
	for row in service_breakdown:
		row["count_pct"] = int(round((row["count"] / max(1, len(items))) * 100))
		row["stock_pct"] = int(round((row["stock"] / max(1, total_stock)) * 100))

	return {
		"total_items": len(items),
		"total_stock": total_stock,
		"total_inventory_value": total_value,
		"low_stock_items": low_stock_items,
		"service_breakdown": service_breakdown,
		"max_service_count": max_service_count,
		"max_service_stock": max_service_stock,
		"recent_items": recent_items,
	}


def _build_product_payload(cleaned_data):
	return {
		"name": cleaned_data["name"],
		"brand": cleaned_data["brand"],
		"description": cleaned_data.get("description", ""),
		"image_url": cleaned_data.get("image_url", ""),
		"price": str(cleaned_data["price"]),
		"stock": cleaned_data["stock"],
	}


def staff_login_view(request):
	if request.user.is_authenticated and request.user.is_staff:
		return redirect("staff_dashboard")

	form = StaffLoginForm(request, data=request.POST or None)
	if request.method == "POST" and form.is_valid():
		user = form.get_user()
		if not user.is_staff:
			messages.error(request, "This account does not have Staff access.")
		else:
			login(request, user)
			return redirect("staff_dashboard")

	return render(request, "staff/login.html", {"form": form})


def staff_register_view(request):
	form = StaffRegisterForm(request.POST or None)
	if request.method == "POST" and form.is_valid():
		user = User.objects.create_user(
			username=form.cleaned_data["username"],
			email=form.cleaned_data["email"],
			password=form.cleaned_data["password"],
		)
		user.is_staff = True
		user.is_superuser = False
		user.save(update_fields=["is_staff", "is_superuser"])
		messages.success(request, "Staff account created successfully. Please sign in.")
		return redirect("staff_login")

	return render(request, "staff/register.html", {"form": form})


@login_required
def staff_logout_view(request):
	logout(request)
	return redirect("staff_login")


@login_required
@user_passes_test(_is_staff_user)
@require_http_methods(["GET"])
def staff_dashboard_view(request):
	range_days = _resolve_range_days(request.GET.get("range"))
	context = _build_dashboard_stats()
	context.update(_fetch_customer_analytics(customer_limit=120, recent_limit=12, range_days=range_days))
	context["selected_range_days"] = range_days
	context["time_ranges"] = [7, 30, 90]
	context["revenue_trend_daily_rows"] = _build_trend_rows(context.get("revenue_trend_daily"))
	context["revenue_trend_weekly_rows"] = _build_trend_rows(context.get("revenue_trend_weekly"))
	return render(request, "staff/dashboard.html", context)


@login_required
@user_passes_test(_is_staff_user)
@require_http_methods(["GET"])
def staff_customers_view(request):
	range_days = _resolve_range_days(request.GET.get("range"))
	context = _fetch_customer_analytics(customer_limit=220, recent_limit=30, range_days=range_days)
	query = (request.GET.get("q") or "").strip().lower()
	rows = context.get("customer_rows") or []
	if query:
		rows = [
			row
			for row in rows
			if query in (row.get("username") or "").lower()
			or query in (row.get("email") or "").lower()
			or query in (row.get("display_name") or "").lower()
			or query in (row.get("full_name") or "").lower()
		]

	page_size = 24
	rows_page = Paginator(rows, page_size).get_page(request.GET.get("page") or 1)
	history_customers = [
		row for row in rows_page.object_list if _to_int(row.get("paid_order_count")) > 0
	][:10]

	context["customer_rows_page"] = rows_page
	context["history_customers"] = history_customers
	context["customer_query"] = query
	context["filtered_customer_count"] = len(rows)
	context["selected_range_days"] = range_days
	context["time_ranges"] = [7, 30, 90]
	return render(request, "staff/customers.html", context)


@login_required
@user_passes_test(_is_staff_user)
@require_http_methods(["GET", "POST"])
def staff_items_view(request):
	selected_service = _resolve_service_filter(request.GET.get("service"))
	create_initial_service = selected_service if selected_service in SUPPORTED_SERVICES else "laptop"
	create_form = CreateItemForm(prefix="create", initial={"service": create_initial_service})
	update_form = UpdateItemForm(prefix="update")

	if request.method == "POST":
		headers = {"X-Staff-Key": os.getenv("STAFF_API_KEY", "dev-staff-key")}
		intent = (request.POST.get("intent") or "").strip().lower()
		return_service = _resolve_service_filter(request.POST.get("return_service") or selected_service)

		if intent == "create":
			create_form = CreateItemForm(request.POST, prefix="create")
			if create_form.is_valid():
				cleaned = create_form.cleaned_data
				service_name = cleaned["service"]
				endpoint = f"{_service_url(service_name)}/api/products/"
				try:
					response = requests.post(
						endpoint,
						json=_build_product_payload(cleaned),
						headers=headers,
						timeout=8,
					)
					if response.status_code in {200, 201}:
						messages.success(request, "Created new product successfully.")
					else:
						messages.error(request, f"Unable to create product. Status: {response.status_code}")
				except requests.RequestException:
					messages.error(request, "Connection error while creating product.")
			else:
				messages.error(request, "Please fill all required fields to create a product.")

		elif intent == "update":
			update_form = UpdateItemForm(request.POST, prefix="update")
			if update_form.is_valid():
				cleaned = update_form.cleaned_data
				service_name = cleaned["service"]
				product_id = cleaned["product_id"]
				endpoint = f"{_service_url(service_name)}/api/products/{product_id}/"
				try:
					response = requests.put(
						endpoint,
						json=_build_product_payload(cleaned),
						headers=headers,
						timeout=8,
					)
					if response.status_code in {200, 204}:
						messages.success(request, "Updated product successfully.")
					else:
						messages.error(request, f"Unable to update product. Status: {response.status_code}")
				except requests.RequestException:
					messages.error(request, "Connection error while updating product.")
			else:
				messages.error(request, "Selected product data is invalid for update.")

		elif intent == "delete":
			delete_form = DeleteItemForm(request.POST, prefix="delete")
			if delete_form.is_valid():
				cleaned = delete_form.cleaned_data
				service_name = cleaned["service"]
				product_id = cleaned["product_id"]
				endpoint = f"{_service_url(service_name)}/api/products/{product_id}/"
				try:
					response = requests.delete(endpoint, headers=headers, timeout=8)
					if response.status_code in {200, 204}:
						messages.success(request, "Deleted product successfully.")
					else:
						messages.error(request, f"Unable to delete product. Status: {response.status_code}")
				except requests.RequestException:
					messages.error(request, "Connection error while deleting product.")
			else:
				messages.error(request, "Delete request is invalid.")

		else:
			messages.error(request, "Unknown action requested.")

		return redirect(f"/staff/items/?service={return_service}")

	items = _fetch_dashboard_items(selected_service)
	context = {
		"create_form": create_form,
		"update_form": update_form,
		"items": items,
		"selected_service": selected_service,
	}
	return render(request, "staff/items.html", context)
