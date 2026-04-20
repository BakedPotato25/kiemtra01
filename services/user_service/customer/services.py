import os
from decimal import Decimal, InvalidOperation

import requests
from django.contrib.auth import get_user_model


User = get_user_model()

LEGACY_CATEGORY_ALIASES = {
    "laptop": {"business-laptops", "gaming-laptops", "ultrabooks"},
    "mobile": {"smartphones", "tablets", "smartwatches"},
    "accessory": {"audio", "keyboards-mice", "chargers-cables", "bags-stands"},
}
DEFAULT_CATEGORY_HERO = "https://images.unsplash.com/photo-1498049794561-7780e7231661?auto=format&fit=crop&w=1400&q=80"
FALLBACK_CATEGORY_FIXTURES = [
    {
        "slug": "business-laptops",
        "name": "Business Laptops",
        "description": "Reliable laptops for office, remote teams, and productivity-heavy workflows.",
        "hero_image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 10,
    },
    {
        "slug": "gaming-laptops",
        "name": "Gaming Laptops",
        "description": "High-performance gaming notebooks with dedicated graphics and cooling headroom.",
        "hero_image_url": "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 20,
    },
    {
        "slug": "ultrabooks",
        "name": "Ultrabooks",
        "description": "Lightweight premium laptops optimized for mobility, battery life, and clean design.",
        "hero_image_url": "https://images.unsplash.com/photo-1517336714739-489689fd1ca8?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 30,
    },
    {
        "slug": "smartphones",
        "name": "Smartphones",
        "description": "Modern phones for photography, communication, productivity, and social media creation.",
        "hero_image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 40,
    },
    {
        "slug": "tablets",
        "name": "Tablets",
        "description": "Portable tablets for note-taking, drawing, media, and flexible productivity.",
        "hero_image_url": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 50,
    },
    {
        "slug": "smartwatches",
        "name": "Smartwatches",
        "description": "Health, fitness, and notification-focused wearables for daily convenience.",
        "hero_image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 60,
    },
    {
        "slug": "audio",
        "name": "Audio",
        "description": "Headphones, earbuds, microphones, and speakers for communication and entertainment.",
        "hero_image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 70,
    },
    {
        "slug": "keyboards-mice",
        "name": "Keyboards & Mice",
        "description": "Input devices for productivity, ergonomic comfort, and responsive control.",
        "hero_image_url": "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 80,
    },
    {
        "slug": "chargers-cables",
        "name": "Chargers & Cables",
        "description": "Charging accessories, travel power gear, and essential connectivity tools.",
        "hero_image_url": "https://images.unsplash.com/photo-1583394838336-acd977736f90?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 90,
    },
    {
        "slug": "bags-stands",
        "name": "Bags & Stands",
        "description": "Carry gear, protective bags, and stands that improve comfort and mobility.",
        "hero_image_url": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=1400&q=80",
        "sort_order": 100,
    },
]


def _product_service_url():
    return (os.getenv("PRODUCT_SERVICE_URL") or "http://product-service:8000").rstrip("/")


def _order_service_url():
    return (os.getenv("ORDER_SERVICE_URL") or "http://order-service:8000").rstrip("/")


def _order_internal_key():
    return str(
        os.getenv("ORDER_SERVICE_INTERNAL_KEY")
        or os.getenv("STAFF_API_KEY")
        or "dev-order-internal-key"
    ).strip()


def _chatbot_service_url():
    return (os.getenv("CHATBOT_SERVICE_URL") or "http://chatbot-service:8000").rstrip("/")


def _price_bounds(price_range):
    mapping = {
        "under_500": (None, Decimal("500")),
        "500_1000": (Decimal("500"), Decimal("1000")),
        "1000_2000": (Decimal("1000"), Decimal("2000")),
        "above_2000": (Decimal("2000"), None),
    }
    return mapping.get(price_range, (None, None))


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_decimal(value, default=Decimal("0")):
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        return default


def _request_json(method, url, *, params=None, payload=None, headers=None, timeout=8):
    try:
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        data = response.json() if response.content else {}
    except ValueError:
        return {"ok": False, "status_code": 502, "data": {}, "error": "invalid_response"}
    except requests.RequestException:
        return {"ok": False, "status_code": 503, "data": {}, "error": "service_unavailable"}

    return {
        "ok": response.ok,
        "status_code": response.status_code,
        "data": data if isinstance(data, dict) else {"results": data},
        "error": None if response.ok else (data.get("error") if isinstance(data, dict) else "upstream_error"),
    }


def category_alias_for_slug(category_slug):
    normalized = str(category_slug or "").strip().lower()
    for alias, categories in LEGACY_CATEGORY_ALIASES.items():
        if normalized in categories:
            return alias
    return normalized


def _category_matches_filter(category_slug, selected_category):
    selected = str(selected_category or "all").strip().lower()
    if selected in {"", "all"}:
        return True
    if selected == category_slug:
        return True
    if selected in LEGACY_CATEGORY_ALIASES:
        return category_slug in LEGACY_CATEGORY_ALIASES[selected]
    return False


def _normalize_product(item):
    category_slug = str(item.get("category_slug") or "").strip().lower()
    category_name = str(item.get("category_name") or "").strip()
    return {
        "service": category_slug,
        "service_group": category_alias_for_slug(category_slug),
        "category_slug": category_slug,
        "category_name": category_name,
        "id": item.get("id"),
        "name": item.get("name", "N/A"),
        "description": item.get("description", ""),
        "image_url": item.get("image_url", ""),
        "brand": item.get("brand", ""),
        "price": str(item.get("price", "0")),
        "stock": _safe_int(item.get("stock"), 0),
    }


def fetch_categories():
    response = _request_json("GET", f"{_product_service_url()}/api/categories/", timeout=6)
    if response["ok"]:
        items = response["data"].get("results", response["data"])
        if isinstance(items, list):
            return [
                {
                    "id": item.get("id"),
                    "slug": item["slug"],
                    "name": item["name"],
                    "description": item.get("description") or "",
                    "hero_image_url": item.get("hero_image_url") or DEFAULT_CATEGORY_HERO,
                    "sort_order": _safe_int(item.get("sort_order"), 0),
                }
                for item in items
                if item.get("slug") and item.get("name")
            ]
    return [{**item, "id": None} for item in FALLBACK_CATEGORY_FIXTURES]


def fetch_category_lookup():
    return {item["slug"]: item for item in fetch_categories()}


def build_category_sections(limit=6):
    sections = []
    for item in fetch_categories()[: max(1, limit)]:
        sections.append(
            {
                "title": item["name"],
                "description": item.get("description") or f"Browse products from the {item['name']} catalog.",
                "query": item["slug"],
                "hero_image_url": item.get("hero_image_url") or DEFAULT_CATEGORY_HERO,
            }
        )
    return sections


def category_choice_pairs(include_all=False, include_aliases=False):
    choices = []
    if include_aliases:
        choices.extend(
            [
                ("laptop", "Laptop Group"),
                ("mobile", "Mobile Group"),
                ("accessory", "Accessories Group"),
            ]
        )
    choices.extend((item["slug"], item["name"]) for item in fetch_categories())
    if include_all:
        return [("all", "All categories"), *choices]
    return choices


def _sort_products(products, sort_by):
    def price_value(product):
        return _safe_decimal(product.get("price"))

    if sort_by == "price_low_high":
        return sorted(products, key=price_value)
    if sort_by == "price_high_low":
        return sorted(products, key=price_value, reverse=True)
    if sort_by == "name_az":
        return sorted(products, key=lambda p: (p["name"] or "").lower())
    if sort_by == "name_za":
        return sorted(products, key=lambda p: (p["name"] or "").lower(), reverse=True)
    return sorted(products, key=lambda p: _safe_int(p.get("id"), 0), reverse=True)


def fetch_products(filters=None):
    filters = filters or {}
    params = {}
    if filters.get("q"):
        params["search"] = filters["q"]
    if filters.get("brand") and filters.get("brand") != "all":
        params["brand"] = filters["brand"]
    min_price, max_price = _price_bounds(filters.get("price_range", "all"))
    if min_price is not None:
        params["min_price"] = str(min_price)
    if max_price is not None:
        params["max_price"] = str(max_price)
    if filters.get("stock") == "in_stock":
        params["in_stock"] = "true"

    selected_category = (filters.get("category") or filters.get("service") or "all").strip().lower()
    if selected_category not in {"all", *LEGACY_CATEGORY_ALIASES.keys()}:
        params["category"] = selected_category

    response = _request_json("GET", f"{_product_service_url()}/api/products/", params=params, timeout=6)
    if not response["ok"]:
        return []

    items = response["data"].get("results", response["data"])
    if not isinstance(items, list):
        return []

    normalized = [_normalize_product(item) for item in items]
    normalized = [item for item in normalized if _category_matches_filter(item["category_slug"], selected_category)]
    for product in normalized:
        product["price_number"] = _safe_decimal(product["price"])
    return _sort_products(normalized, filters.get("sort", "newest"))


def get_available_brands(products):
    return sorted({(product.get("brand") or "").strip() for product in products if (product.get("brand") or "").strip()})


def fetch_product_detail(category_slug, product_id):
    response = _request_json("GET", f"{_product_service_url()}/api/products/{product_id}/", timeout=6)
    if not response["ok"]:
        return None
    product = _normalize_product(response["data"])
    if not _category_matches_filter(product["category_slug"], category_slug):
        return None
    return product


def _order_request(method, path, *, params=None, payload=None, timeout=8):
    return _request_json(
        method,
        f"{_order_service_url()}{path}",
        params=params,
        payload=payload,
        headers={"X-Internal-Key": _order_internal_key()},
        timeout=timeout,
    )


def list_cart_items(user_id):
    response = _order_request("GET", "/api/cart/", params={"user_id": user_id})
    return response["data"].get("items", []) if response["ok"] else []


def add_to_cart(user_id, payload):
    response = _order_request("POST", "/api/cart/", payload={"user_id": user_id, **payload})
    return response["ok"], response["data"], response["error"]


def remove_from_cart(user_id, item_id):
    response = _order_request("DELETE", f"/api/cart/{item_id}/", params={"user_id": user_id})
    return response["ok"], response["error"]


def list_saved_items(user_id):
    response = _order_request("GET", "/api/saved/", params={"user_id": user_id})
    return response["data"].get("items", []) if response["ok"] else []


def toggle_saved_item(user_id, payload):
    response = _order_request("POST", "/api/saved/toggle/", payload={"user_id": user_id, **payload})
    return response["ok"], response["data"], response["error"]


def list_compare_items(user_id):
    response = _order_request("GET", "/api/compare/", params={"user_id": user_id})
    return response["data"].get("items", []) if response["ok"] else []


def toggle_compare_item(user_id, payload):
    response = _order_request("POST", "/api/compare/toggle/", payload={"user_id": user_id, **payload})
    return response["ok"], response["data"], response["error"]


def remove_compare_item(user_id, item_id):
    response = _order_request("DELETE", f"/api/compare/{item_id}/", params={"user_id": user_id})
    return response["ok"], response["error"]


def checkout_order(user_id, shipping_data):
    response = _order_request("POST", "/api/checkout/", payload={"user_id": user_id, **shipping_data}, timeout=10)
    return response["ok"], response["data"].get("order"), response["error"]


def list_orders(user_id):
    response = _order_request("GET", "/api/orders/", params={"user_id": user_id})
    return response["data"].get("orders", []) if response["ok"] else []


def pay_order(user_id, order_id):
    response = _order_request("POST", f"/api/orders/{order_id}/pay/", payload={"user_id": user_id})
    return response["ok"], response["data"].get("order"), response["error"]


def fetch_staff_orders(limit=80, payment_status="", shipping_status=""):
    params = {"limit": limit}
    if payment_status:
        params["payment_status"] = payment_status
    if shipping_status:
        params["shipping_status"] = shipping_status
    response = _order_request("GET", "/api/staff/orders/", params=params)
    return response["data"].get("orders", []) if response["ok"] else []


def update_shipping_status(order_id, shipping_status):
    response = _order_request(
        "POST",
        f"/api/staff/orders/{order_id}/shipping/",
        payload={"shipping_status": shipping_status},
    )
    return response["ok"], response["data"].get("order"), response["error"]


def fetch_order_analytics(customer_limit=200, recent_limit=20, range_days=30):
    response = _order_request(
        "GET",
        "/api/analytics/customers/",
        params={
            "customer_limit": customer_limit,
            "recent_limit": recent_limit,
            "range_days": range_days,
        },
    )
    return response["data"] if response["ok"] else {}


def build_staff_analytics_payload(customer_limit=200, recent_limit=20, range_days=30):
    payload = fetch_order_analytics(customer_limit=customer_limit, recent_limit=recent_limit, range_days=range_days)
    user_ids = [row.get("user_id") for row in payload.get("customer_rows", []) if row.get("user_id")]
    users = User.objects.filter(id__in=user_ids)
    user_map = {user.id: user for user in users}

    def enrich_row(row):
        user = user_map.get(row.get("user_id"))
        full_name = ""
        username = ""
        email = ""
        if user:
            full_name = " ".join([user.first_name or "", user.last_name or ""]).strip()
            username = user.username
            email = user.email or ""
        return {
            **row,
            "display_name": full_name or username or f"User {row.get('user_id')}",
            "full_name": full_name,
            "username": username,
            "email": email,
        }

    payload["customer_rows"] = [enrich_row(row) for row in payload.get("customer_rows", [])]
    payload["top_customers"] = payload["customer_rows"][:8]

    enriched_recent_orders = []
    for row in payload.get("recent_orders", []):
        user = user_map.get(row.get("user_id"))
        enriched_recent_orders.append(
            {
                **row,
                "username": user.username if user else "",
                "display_name": " ".join([user.first_name or "", user.last_name or ""]).strip() or (user.username if user else f"User {row.get('user_id')}"),
            }
        )
    payload["recent_orders"] = enriched_recent_orders
    return payload


def export_behavior_source(max_users=300, max_events=1200, source_status="paid"):
    response = _order_request(
        "GET",
        "/api/internal/behavior-source/",
        params={
            "max_users": max_users,
            "max_events": max_events,
            "source_status": source_status,
        },
        timeout=10,
    )
    return response["data"].get("records", []) if response["ok"] else []


def build_user_context_payload(user_id):
    cart_items = [item.get("product_name") for item in list_cart_items(user_id)[:6]]
    saved_items = [item.get("product_name") for item in list_saved_items(user_id)[:6]]
    recent_paid_items = []
    for order in list_orders(user_id):
        if order.get("payment_status") != "paid":
            continue
        for item in order.get("items", []):
            name = item.get("product_name")
            if name and name not in recent_paid_items:
                recent_paid_items.append(name)
            if len(recent_paid_items) >= 8:
                break
        if len(recent_paid_items) >= 8:
            break
    return {
        "cart_items": cart_items[:4],
        "saved_items": saved_items[:4],
        "recent_paid_items": recent_paid_items[:4],
    }


def request_chatbot_reply(question, current_product=None, user_context=None, user_ref="", limit=5):
    base_url = _chatbot_service_url()
    timeout_seconds = max(10, int(os.getenv("CHATBOT_REQUEST_TIMEOUT_SECONDS", "40") or "40"))
    retry_count = max(1, int(os.getenv("CHATBOT_REQUEST_RETRIES", "2") or "2"))
    endpoint = f"{base_url}/api/chat/reply/" if not base_url.endswith("/api/chat/reply") else f"{base_url}/"
    payload = {
        "message": (question or "").strip(),
        "current_product": current_product or None,
        "user_context": user_context or {},
        "user_ref": str(user_ref or "").strip(),
        "limit": max(1, int(limit or 5)),
    }

    response = None
    data = {}
    for attempt in range(retry_count):
        try:
            response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
            data = response.json() if response.content else {}
            break
        except requests.ReadTimeout:
            if attempt + 1 >= retry_count:
                return {
                    "answer": "Chatbot service is temporarily unavailable. Please try again.",
                    "recommendations": [],
                    "citations": [],
                    "source": "chatbot_service_unavailable",
                    "fallback_used": True,
                    "error_code": "service_timeout",
                }
        except (requests.RequestException, ValueError):
            return {
                "answer": "Chatbot service is temporarily unavailable. Please try again.",
                "recommendations": [],
                "citations": [],
                "source": "chatbot_service_unavailable",
                "fallback_used": True,
                "error_code": "service_unavailable",
            }

    if response is None or not response.ok or not isinstance(data, dict):
        return {
            "answer": "Chatbot service could not process your request.",
            "recommendations": [],
            "citations": [],
            "source": "chatbot_service_error",
            "fallback_used": True,
            "error_code": "upstream_error",
        }

    return {
        "answer": data.get("answer") or "No response generated.",
        "recommendations": data.get("recommendations") or [],
        "citations": data.get("citations") or [],
        "source": data.get("source") or "chatbot_service",
        "fallback_used": bool(data.get("fallback_used")),
        "error_code": data.get("error_code"),
        "provider": data.get("provider"),
    }


def recommend_products_for_detail(current_product, cart_items=None, limit=6, mode="mixed"):
    current_product = current_product or {}
    cart_items = cart_items or []
    mode = (mode or "mixed").strip().lower()
    products = fetch_products({"category": "all", "sort": "newest"})
    if not products:
        return []

    current_id = _safe_int(current_product.get("id"), 0)
    current_category = str(current_product.get("category_slug") or current_product.get("service") or "").strip().lower()
    current_brand = str(current_product.get("brand") or "").strip().lower()
    current_price = _safe_decimal(current_product.get("price"))
    cart_counts = {}
    for item in cart_items:
        category_slug = str(item.get("category_slug") or item.get("product_service") or "").strip().lower()
        cart_counts[category_slug] = cart_counts.get(category_slug, 0) + _safe_int(item.get("quantity"), 1)

    candidates = []
    for product in products:
        if _safe_int(product.get("id"), 0) == current_id:
            continue
        if mode == "similar" and product.get("category_slug") != current_category:
            continue

        score = Decimal("0")
        if product.get("stock", 0) > 0:
            score += Decimal("3")
        else:
            score -= Decimal("5")
        if product.get("category_slug") == current_category:
            score += Decimal("2")
        if current_brand and (product.get("brand") or "").strip().lower() == current_brand:
            score += Decimal("1.5")
        if current_price > 0:
            candidate_price = _safe_decimal(product.get("price"))
            delta_ratio = abs(candidate_price - current_price) / current_price if candidate_price > 0 else Decimal("1")
            if delta_ratio <= Decimal("0.15"):
                score += Decimal("1.5")
            elif delta_ratio <= Decimal("0.35"):
                score += Decimal("0.8")
        score += Decimal(str(min(cart_counts.get(product.get("category_slug"), 0), 3))) * Decimal("0.5")
        candidates.append((score, product))

    candidates.sort(key=lambda row: (row[0], _safe_int(row[1].get("id"), 0)), reverse=True)
    return [row[1] for row in candidates[: max(1, limit)]]
