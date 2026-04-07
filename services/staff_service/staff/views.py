import os

import requests
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CreateItemForm, DeleteItemForm, StaffLoginForm, StaffRegisterForm, UpdateItemForm

User = get_user_model()
SUPPORTED_SERVICES = ("laptop", "mobile", "accessory")


def _is_staff_user(user):
	return user.is_authenticated and user.is_staff


def _service_url(service_name):
	if service_name == "accessory":
		return os.getenv("ACCESSORY_SERVICE_URL", "http://accessory-service:8000")
	if service_name == "mobile":
		return os.getenv("MOBILE_SERVICE_URL", "http://mobile-service:8000")
	return os.getenv("LAPTOP_SERVICE_URL", "http://laptop-service:8000")


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
@require_http_methods(["GET", "POST"])
def staff_dashboard_view(request):
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

		return redirect(f"/staff/dashboard/?service={return_service}")

	items = _fetch_dashboard_items(selected_service)
	context = {
		"create_form": create_form,
		"update_form": update_form,
		"items": items,
		"selected_service": selected_service,
		"service_filters": ["all", *SUPPORTED_SERVICES],
	}
	return render(request, "staff/dashboard.html", context)
