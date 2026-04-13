from decimal import Decimal, InvalidOperation
from datetime import timedelta
import json
import os

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from .content import CATEGORY_SECTIONS, FAQ_ITEMS
from .forms import CustomerLoginForm, CustomerRegisterForm, ProductFilterForm
from .models import BlogPost, CartItem, CompareItem, Order, OrderItem, SavedItem, Testimonial
from .api_gateway.registry import build_gateway_registry
from .services import (
    fetch_product_detail,
    fetch_products,
    get_available_brands,
    request_chatbot_reply,
    recommend_products_for_detail,
)

User = get_user_model()


def _is_customer_user(user):
    return user.is_authenticated and not user.is_staff and not user.is_superuser


def gateway_dashboard_view(request):
    gateway_payload = build_gateway_registry(request)
    return render(request, "customer/gateway_dashboard.html", {"gateway": gateway_payload})


def gateway_apis_view(request):
    gateway_payload = build_gateway_registry(request)
    return JsonResponse(gateway_payload)


def _safe_next_url(next_url, fallback):
    next_url = (next_url or "").strip()
    if next_url.startswith("/"):
        return next_url
    return fallback


def _dashboard_url(request, updates=None, anchor=None):
    updates = updates or {}
    query = request.GET.copy()
    for key, value in updates.items():
        if value in [None, ""]:
            query.pop(key, None)
        else:
            query[key] = str(value)

    encoded = query.urlencode()
    url = "/customer/dashboard/"
    if encoded:
        url += f"?{encoded}"
    if anchor:
        url += f"#{anchor}"
    return url


def _default_filters():
    return {
        "q": "",
        "category": "all",
        "stock": "all",
        "price_range": "all",
        "sort": "newest",
        "brand": "all",
    }


def _collect_filters(request):
    filters = _default_filters()
    for key in filters:
        value = request.GET.get(key)
        if value is not None and value != "":
            filters[key] = value

    brand_scope_filters = dict(filters)
    brand_scope_filters["brand"] = "all"
    brand_scope_filters["sort"] = "newest"
    brand_source_products = fetch_products(brand_scope_filters)
    available_brands = get_available_brands(brand_source_products)

    form = ProductFilterForm(request.GET or None, brand_choices=available_brands)
    if form.is_valid():
        cleaned = form.cleaned_data
        for key in filters:
            value = cleaned.get(key)
            if value not in [None, ""]:
                filters[key] = value

    if filters["brand"] not in ["all", *available_brands]:
        filters["brand"] = "all"

    return form, filters, available_brands


def _parse_product_payload(request):
    service = (request.POST.get("product_service", "") or "").strip().lower()
    allowed_services = {
        CartItem.SERVICE_LAPTOP,
        CartItem.SERVICE_MOBILE,
        CartItem.SERVICE_ACCESSORY,
    }
    if service not in allowed_services:
        return None

    try:
        product_id = int(request.POST.get("product_id", "0"))
        price = Decimal(str(request.POST.get("unit_price", "0")))
        stock = int(request.POST.get("stock", "0") or 0)
    except (TypeError, ValueError, InvalidOperation):
        return None

    return {
        "product_service": service,
        "product_id": product_id,
        "product_name": (request.POST.get("product_name", "") or "").strip()[:255],
        "product_brand": (request.POST.get("product_brand", "") or "").strip()[:120],
        "product_image_url": (request.POST.get("product_image_url", "") or "").strip(),
        "unit_price": price,
        "stock": max(0, stock),
    }


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_request_payload(request):
    content_type = (request.content_type or "").lower()
    if "application/json" in content_type:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return request.POST.dict()


def _extract_current_product(payload):
    current_product = payload.get("current_product")
    if not isinstance(current_product, dict):
        return None

    service = str(current_product.get("service") or "").strip().lower()
    if service not in {"laptop", "mobile", "accessory"}:
        return None

    product_id = _safe_int(current_product.get("id"), 0)
    if product_id <= 0:
        return None

    return {
        "service": service,
        "id": product_id,
        "name": str(current_product.get("name") or "").strip()[:255],
        "brand": str(current_product.get("brand") or "").strip()[:120],
        "price": str(current_product.get("price") or "0").strip(),
    }


def _unique_strings(items, limit):
    unique_items = []
    seen = set()
    for item in items:
        value = (item or "").strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique_items.append(value)
        if len(unique_items) >= limit:
            break
    return unique_items


def _build_user_context_payload(user):
    cart_items = list(CartItem.objects.filter(user=user).values_list("product_name", flat=True)[:6])
    saved_items = list(SavedItem.objects.filter(user=user).values_list("product_name", flat=True)[:6])
    recent_paid_items = list(
        OrderItem.objects.filter(order__user=user, order__status=Order.STATUS_PAID)
        .order_by("-id")
        .values_list("product_name", flat=True)[:8]
    )

    return {
        "cart_items": _unique_strings(cart_items, 4),
        "saved_items": _unique_strings(saved_items, 4),
        "recent_paid_items": _unique_strings(recent_paid_items, 4),
    }


def _decimal_to_str(value):
    return f"{(value or Decimal('0')):.2f}"


def _resolve_range_days(raw_value):
    value = _safe_int(raw_value, 30)
    if value in {7, 30, 90}:
        return value
    return 30


def _format_datetime_short(value):
    if value is None:
        return None
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M")


def _build_staff_analytics_payload(customer_limit=200, recent_limit=20, range_days=30):
    customers = list(
        User.objects.filter(is_staff=False, is_superuser=False)
        .order_by("id")[: max(1, customer_limit)]
    )
    customer_ids = [customer.id for customer in customers]
    now = timezone.now()
    start_time = now - timedelta(days=max(1, range_days))

    customer_rows = {}
    for customer in customers:
        full_name = " ".join([customer.first_name or "", customer.last_name or ""]).strip()
        display_name = full_name or customer.username
        customer_rows[customer.id] = {
            "user_id": customer.id,
            "display_name": display_name,
            "full_name": full_name,
            "username": customer.username,
            "email": customer.email or "",
            "order_count": 0,
            "paid_order_count": 0,
            "total_units": 0,
            "total_spent_value": Decimal("0"),
            "last_order_at": None,
            "recent_paid_orders": [],
        }

    orders = list(
        Order.objects.filter(user_id__in=customer_ids, created_at__gte=start_time)
        .select_related("user")
        .prefetch_related("items")
        .order_by("-created_at")
    )

    daily_revenue = {}
    for offset in range(range_days - 1, -1, -1):
        day = (now - timedelta(days=offset)).date()
        daily_revenue[day] = Decimal("0")

    weekly_revenue = {}
    for day in daily_revenue:
        week_start = day - timedelta(days=day.weekday())
        weekly_revenue.setdefault(week_start, Decimal("0"))

    total_orders = 0
    paid_orders = 0
    pending_orders = 0
    cancelled_orders = 0
    total_revenue = Decimal("0")
    total_units_sold = 0
    recent_orders = []

    for order in orders:
        total_orders += 1
        order_total = order.total_amount or Decimal("0")
        order_items = list(order.items.all())
        order_units = sum(item.quantity for item in order_items)
        total_units_sold += order_units

        if order.status == Order.STATUS_PAID:
            paid_orders += 1
            total_revenue += order_total
        elif order.status == Order.STATUS_PENDING:
            pending_orders += 1
        elif order.status == Order.STATUS_CANCELLED:
            cancelled_orders += 1

        customer_row = customer_rows.get(order.user_id)
        if customer_row is not None:
            customer_row["order_count"] += 1
            if customer_row["last_order_at"] is None:
                customer_row["last_order_at"] = _format_datetime_short(order.created_at)

            if order.status == Order.STATUS_PAID:
                customer_row["paid_order_count"] += 1
                customer_row["total_units"] += order_units
                customer_row["total_spent_value"] += order_total

                order_day = timezone.localtime(order.created_at).date()
                if order_day in daily_revenue:
                    daily_revenue[order_day] += order_total
                week_start = order_day - timedelta(days=order_day.weekday())
                if week_start in weekly_revenue:
                    weekly_revenue[week_start] += order_total

                if len(customer_row["recent_paid_orders"]) < 5:
                    customer_row["recent_paid_orders"].append(
                        {
                            "order_id": order.id,
                            "created_at": _format_datetime_short(order.created_at),
                            "total_amount": _decimal_to_str(order_total),
                        }
                    )

        if len(recent_orders) < max(1, recent_limit):
            preview_items = []
            for item in order_items[:3]:
                preview_items.append(f"{item.product_name} x{item.quantity}")

            recent_orders.append(
                {
                    "order_id": order.id,
                    "username": order.user.username,
                    "display_name": customer_row.get("display_name") if customer_row else order.user.username,
                    "status": order.status,
                    "total_amount": _decimal_to_str(order_total),
                    "total_units": order_units,
                    "created_at": _format_datetime_short(order.created_at),
                    "items_preview": ", ".join(preview_items),
                }
            )

    finalized_rows = []
    for row in customer_rows.values():
        total_spent_value = row.pop("total_spent_value")
        row["total_spent"] = _decimal_to_str(total_spent_value)
        finalized_rows.append(row)

    finalized_rows.sort(
        key=lambda item: (
            Decimal(item["total_spent"]),
            item["order_count"],
            item["username"].lower(),
        ),
        reverse=True,
    )

    avg_paid_order_value = total_revenue / paid_orders if paid_orders else Decimal("0")
    active_customers = sum(1 for row in finalized_rows if row["order_count"] > 0)

    daily_series = [
        {
            "label": day.strftime("%m-%d"),
            "revenue": _decimal_to_str(amount),
        }
        for day, amount in daily_revenue.items()
    ]
    weekly_series = [
        {
            "label": f"Week {week_start.strftime('%m-%d')}",
            "revenue": _decimal_to_str(amount),
        }
        for week_start, amount in weekly_revenue.items()
    ]

    return {
        "customer_count": len(customers),
        "active_customers": active_customers,
        "range_days": range_days,
        "range_start": start_time.date().isoformat(),
        "range_end": now.date().isoformat(),
        "order_stats": {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "pending_orders": pending_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": _decimal_to_str(total_revenue),
            "total_units_sold": total_units_sold,
            "average_paid_order_value": _decimal_to_str(avg_paid_order_value),
        },
        "top_customers": finalized_rows[:8],
        "customer_rows": finalized_rows,
        "recent_orders": recent_orders,
        "revenue_trend_daily": daily_series,
        "revenue_trend_weekly": weekly_series,
    }


def home_view(request):
    if _is_customer_user(request.user):
        return redirect("customer_dashboard")
    return redirect("customer_login")


def customer_login_view(request):
    if _is_customer_user(request.user):
        return redirect("customer_dashboard")

    form = CustomerLoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if user.is_staff or user.is_superuser:
            messages.error(request, "Staff/Admin accounts must sign in from the staff portal.")
            return render(request, "customer/login.html", {"form": form})

        login(request, user)
        return redirect("customer_dashboard")

    return render(request, "customer/login.html", {"form": form})


def customer_register_view(request):
    form = CustomerRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data["username"],
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )
        user.is_staff = False
        user.is_superuser = False
        user.save(update_fields=["is_staff", "is_superuser"])
        messages.success(request, "Registration successful. Please sign in.")
        return redirect("customer_login")

    return render(request, "customer/register.html", {"form": form})


@login_required
def customer_logout_view(request):
    logout(request)
    return redirect("customer_login")


@login_required
@user_passes_test(_is_customer_user)
def customer_dashboard_view(request):
    filter_form, filters, available_brands = _collect_filters(request)
    products = fetch_products(filters)
    saved_pairs = {
        (item.product_service, item.product_id)
        for item in SavedItem.objects.filter(user=request.user).only("product_service", "product_id")
    }
    for product in products:
        try:
            product_id = int(product.get("id") or 0)
        except (TypeError, ValueError):
            product_id = 0
        product["is_saved"] = (product.get("service"), product_id) in saved_pairs

    product_page = Paginator(products, 9).get_page(request.GET.get("product_page") or 1)
    blog_page = Paginator(BlogPost.objects.all(), 3).get_page(request.GET.get("blog_page") or 1)

    all_products = fetch_products(
        {
            "q": "",
            "category": "all",
            "stock": "all",
            "price_range": "all",
            "sort": "newest",
            "brand": "all",
        }
    )
    best_sellers = sorted(all_products, key=lambda p: int(p.get("stock") or 0), reverse=True)[:6]
    testimonials = Testimonial.objects.filter(is_featured=True)[:6]

    cart_count = CartItem.objects.filter(user=request.user).count()

    context = {
        "filter_form": filter_form,
        "products_page": product_page,
        "best_sellers": best_sellers,
        "available_brands": available_brands,
        "cart_count": cart_count,
        "filters": filters,
        "category_sections": CATEGORY_SECTIONS,
        "testimonials": testimonials,
        "blog_page": blog_page,
        "faq_items": FAQ_ITEMS,
        "product_prev_url": _dashboard_url(
            request,
            {"product_page": product_page.previous_page_number() if product_page.has_previous() else None},
            "section-products",
        ),
        "product_next_url": _dashboard_url(
            request,
            {"product_page": product_page.next_page_number() if product_page.has_next() else None},
            "section-products",
        ),
        "blog_prev_url": _dashboard_url(
            request,
            {"blog_page": blog_page.previous_page_number() if blog_page.has_previous() else None},
            "section-stories",
        ),
        "blog_next_url": _dashboard_url(
            request,
            {"blog_page": blog_page.next_page_number() if blog_page.has_next() else None},
            "section-stories",
        ),
    }
    return render(request, "customer/dashboard.html", context)


@login_required
@user_passes_test(_is_customer_user)
@require_POST
def chatbot_reply_view(request):
    payload = _parse_request_payload(request)
    message = str(payload.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "Message is required."}, status=400)

    if len(message) > 500:
        message = message[:500]

    current_product = _extract_current_product(payload)
    user_context = _build_user_context_payload(request.user)

    result = request_chatbot_reply(
        question=message,
        current_product=current_product,
        user_context=user_context,
        user_ref=str(request.user.id),
        limit=5,
    )

    recommendations = []
    for item in result.get("recommendations", []):
        service_name = (item.get("service") or "").strip().lower()
        product_id = _safe_int(item.get("id"), 0)
        if service_name not in {"laptop", "mobile", "accessory"} or product_id <= 0:
            continue

        recommendations.append(
            {
                "service": service_name,
                "id": product_id,
                "name": item.get("name") or "N/A",
                "brand": item.get("brand") or "",
                "price": item.get("price") or "0",
                "stock": _safe_int(item.get("stock"), 0),
                "image_url": item.get("image_url") or "",
                "url": f"/customer/products/{service_name}/{product_id}/",
            }
        )

    return JsonResponse(
        {
            "answer": result.get("answer") or "No response generated.",
            "recommendations": recommendations,
            "citations": result.get("citations") or [],
            "source": result.get("source") or "rule_based",
            "fallback_used": bool(result.get("fallback_used")),
            "error_code": result.get("error_code"),
            "provider": result.get("provider"),
        }
    )


@login_required
@user_passes_test(_is_customer_user)
def blog_detail_view(request, slug):
    blog_post = get_object_or_404(BlogPost, slug=slug)
    related_posts = BlogPost.objects.exclude(id=blog_post.id)[:4]
    return render(
        request,
        "customer/blog_detail.html",
        {
            "blog_post": blog_post,
            "related_posts": related_posts,
        },
    )


@login_required
@user_passes_test(_is_customer_user)
@require_POST
def add_to_cart_view(request):
    payload = _parse_product_payload(request)
    next_url = _safe_next_url(request.POST.get("next"), "/customer/dashboard/")
    if not payload:
        messages.error(request, "Invalid product data.")
        return redirect(next_url)

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product_service=payload["product_service"],
        product_id=payload["product_id"],
        defaults={
            "product_name": payload["product_name"],
            "product_brand": payload["product_brand"],
            "product_image_url": payload["product_image_url"],
            "unit_price": payload["unit_price"],
            "quantity": 1,
        },
    )

    if not created:
        cart_item.quantity += 1
        cart_item.product_name = payload["product_name"]
        cart_item.product_brand = payload["product_brand"]
        cart_item.product_image_url = payload["product_image_url"]
        cart_item.unit_price = payload["unit_price"]
        cart_item.save(
            update_fields=[
                "quantity",
                "product_name",
                "product_brand",
                "product_image_url",
                "unit_price",
                "updated_at",
            ]
        )

    messages.success(request, f"Added '{payload['product_name']}' to cart.")
    return redirect(next_url)


@login_required
@user_passes_test(_is_customer_user)
@require_POST
def toggle_save_view(request):
    payload = _parse_product_payload(request)
    next_url = _safe_next_url(request.POST.get("next"), "/customer/dashboard/")
    if not payload:
        messages.error(request, "Unable to save this product.")
        return redirect(next_url)

    existing = SavedItem.objects.filter(
        user=request.user,
        product_service=payload["product_service"],
        product_id=payload["product_id"],
    ).first()

    if existing:
        existing.delete()
        messages.success(request, "Removed from saved items.")
    else:
        SavedItem.objects.create(
            user=request.user,
            product_service=payload["product_service"],
            product_id=payload["product_id"],
            product_name=payload["product_name"],
            product_brand=payload["product_brand"],
            product_image_url=payload["product_image_url"],
            unit_price=payload["unit_price"],
        )
        messages.success(request, "Saved for later.")

    return redirect(next_url)


@login_required
@user_passes_test(_is_customer_user)
@require_POST
def toggle_compare_view(request):
    payload = _parse_product_payload(request)
    next_url = _safe_next_url(request.POST.get("next"), "/customer/dashboard/")
    if not payload:
        messages.error(request, "Unable to compare this product.")
        return redirect(next_url)

    existing = CompareItem.objects.filter(
        user=request.user,
        product_service=payload["product_service"],
        product_id=payload["product_id"],
    ).first()

    if existing:
        existing.delete()
        messages.success(request, "Removed from compare list.")
        return redirect(next_url)

    if CompareItem.objects.filter(user=request.user).count() >= 4:
        messages.error(request, "You can compare up to 4 products at a time.")
        return redirect(next_url)

    CompareItem.objects.create(
        user=request.user,
        product_service=payload["product_service"],
        product_id=payload["product_id"],
        product_name=payload["product_name"],
        product_brand=payload["product_brand"],
        product_image_url=payload["product_image_url"],
        unit_price=payload["unit_price"],
        stock=payload["stock"],
    )
    messages.success(request, "Added to compare list.")
    return redirect(next_url)


@login_required
@user_passes_test(_is_customer_user)
def saved_view(request):
    saved_items = SavedItem.objects.filter(user=request.user)
    return render(request, "customer/saved.html", {"saved_items": saved_items})


@login_required
@user_passes_test(_is_customer_user)
def compare_view(request):
    compare_items = CompareItem.objects.filter(user=request.user)
    return render(request, "customer/compare.html", {"compare_items": compare_items})


@login_required
@user_passes_test(_is_customer_user)
@require_POST
def remove_compare_item_view(request, item_id):
    item = get_object_or_404(CompareItem, id=item_id, user=request.user)
    item.delete()
    messages.success(request, "Item removed from compare list.")
    return redirect("customer_compare")


@login_required
@user_passes_test(_is_customer_user)
def product_detail_view(request, service_name, product_id):
    service_name = (service_name or "").strip().lower()
    product = fetch_product_detail(service_name, product_id)
    if not product:
        messages.error(request, "Product not found.")
        return redirect("customer_dashboard")

    rec_mode = (request.GET.get("rec_mode") or "mixed").strip().lower()
    if rec_mode not in {"mixed", "similar"}:
        rec_mode = "mixed"

    cart_snapshot = list(
        CartItem.objects.filter(user=request.user).values("product_service", "quantity")
    )
    related_products = recommend_products_for_detail(
        current_product=product,
        cart_items=cart_snapshot,
        limit=6,
        mode=rec_mode,
    )

    section_anchor = "#section-recommend-products"
    rec_mode_mixed_url = f"{request.path}?rec_mode=mixed{section_anchor}"
    rec_mode_similar_url = f"{request.path}?rec_mode=similar{section_anchor}"

    tech_fallbacks = {
        "laptop": "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=1400&q=80",
        "mobile": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1400&q=80",
        "accessory": "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=1400&q=80",
    }
    gallery_pools = {
        "laptop": [
            "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?auto=format&fit=crop&w=1400&q=80",
        ],
        "mobile": [
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1510557880182-3f8c2b11d7f8?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1605236453806-6ff36851218e?auto=format&fit=crop&w=1400&q=80",
        ],
        "accessory": [
            "https://images.unsplash.com/photo-1527814050087-3793815479db?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1583394838336-acd977736f90?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1625842268584-8f3296236761?auto=format&fit=crop&w=1400&q=80",
            "https://images.unsplash.com/photo-1518444065439-e933c06ce9cd?auto=format&fit=crop&w=1400&q=80",
        ],
    }
    base_image = product.get("image_url") or tech_fallbacks.get(service_name, tech_fallbacks["accessory"])
    pool = gallery_pools.get(service_name, gallery_pools["accessory"])
    gallery_images = [base_image]
    for image_url in pool:
        if len(gallery_images) == 4:
            break
        if image_url != base_image:
            gallery_images.append(image_url)
    while len(gallery_images) < 4:
        gallery_images.append(base_image)

    is_saved = SavedItem.objects.filter(
        user=request.user,
        product_service=service_name,
        product_id=product_id,
    ).exists()
    is_compared = CompareItem.objects.filter(
        user=request.user,
        product_service=service_name,
        product_id=product_id,
    ).exists()

    return render(
        request,
        "customer/product_detail.html",
        {
            "product": product,
            "related_products": related_products,
            "gallery_images": gallery_images,
            "is_saved": is_saved,
            "is_compared": is_compared,
            "compare_count": CompareItem.objects.filter(user=request.user).count(),
            "share_url": request.build_absolute_uri(request.path),
            "chatbot_current_product": product,
            "rec_mode": rec_mode,
            "rec_mode_mixed_url": rec_mode_mixed_url,
            "rec_mode_similar_url": rec_mode_similar_url,
        },
    )


@login_required
@user_passes_test(_is_customer_user)
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user)
    cart_total = sum(item.total_price for item in cart_items)
    return render(
        request,
        "customer/cart.html",
        {
            "cart_items": cart_items,
            "cart_total": cart_total,
        },
    )


@login_required
@user_passes_test(_is_customer_user)
@require_POST
def remove_from_cart_view(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from your cart.")
    return redirect("customer_cart")


@login_required
@user_passes_test(_is_customer_user)
@require_POST
def checkout_view(request):
    with transaction.atomic():
        cart_items = list(CartItem.objects.select_for_update().filter(user=request.user))
        if not cart_items:
            messages.error(request, "Your cart is empty. Checkout is not available.")
            return redirect("customer_cart")

        total_amount = sum(item.total_price for item in cart_items)
        order = Order.objects.create(user=request.user, total_amount=total_amount, status=Order.STATUS_PENDING)
        order_items = [
            OrderItem(
                order=order,
                product_service=item.product_service,
                product_id=item.product_id,
                product_name=item.product_name,
                product_brand=item.product_brand,
                unit_price=item.unit_price,
                quantity=item.quantity,
            )
            for item in cart_items
        ]
        OrderItem.objects.bulk_create(order_items)
        CartItem.objects.filter(user=request.user).delete()

    messages.success(request, f"Order #{order.id} was created with status PENDING.")
    return redirect("customer_orders")


@login_required
@user_passes_test(_is_customer_user)
def orders_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "customer/orders.html", {"orders": orders})


@login_required
@user_passes_test(_is_customer_user)
@require_POST
def pay_order_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status != Order.STATUS_PENDING:
        messages.error(request, f"Order #{order.id} is not pending, so it cannot be paid.")
        return redirect("customer_orders")

    order.status = Order.STATUS_PAID
    order.save(update_fields=["status"])
    messages.success(request, f"Payment completed successfully for order #{order.id}.")
    return redirect("customer_orders")


@require_http_methods(["GET"])
def staff_order_analytics_view(request):
    provided_key = (request.headers.get("X-Staff-Key") or "").strip()
    expected_key = (os.getenv("STAFF_API_KEY") or "dev-staff-key").strip()
    if provided_key != expected_key:
        return JsonResponse({"error": "Forbidden"}, status=403)

    customer_limit = _safe_int(request.GET.get("customer_limit"), 200)
    recent_limit = _safe_int(request.GET.get("recent_limit"), 20)
    range_days = _resolve_range_days(request.GET.get("range_days"))
    payload = _build_staff_analytics_payload(
        customer_limit=max(20, min(1000, customer_limit)),
        recent_limit=max(5, min(100, recent_limit)),
        range_days=range_days,
    )
    return JsonResponse(payload)
