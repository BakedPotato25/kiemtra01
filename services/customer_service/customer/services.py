import os
import re
from decimal import Decimal, InvalidOperation

import requests


def _price_bounds(price_range):
    mapping = {
        "under_500": (None, Decimal("500")),
        "500_1000": (Decimal("500"), Decimal("1000")),
        "1000_2000": (Decimal("1000"), Decimal("2000")),
        "above_2000": (Decimal("2000"), None),
    }
    return mapping.get(price_range, (None, None))


def _fetch_service_products(service_name, base_url, filters):
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

    try:
        response = requests.get(f"{base_url}/api/products/", params=params, timeout=5)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return []

    items = payload.get("results", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []

    normalized = []
    for item in items:
        normalized.append(
            {
                "service": service_name,
                "id": item.get("id"),
                "name": item.get("name", "N/A"),
                "description": item.get("description", ""),
                "image_url": item.get("image_url", ""),
                "brand": item.get("brand", ""),
                "price": item.get("price", "0"),
                "stock": item.get("stock", 0),
            }
        )
    return normalized


def _sort_products(products, sort_by):
    def price_value(product):
        try:
            return Decimal(str(product.get("price", "0")))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0")

    if sort_by == "price_low_high":
        return sorted(products, key=price_value)
    if sort_by == "price_high_low":
        return sorted(products, key=price_value, reverse=True)
    if sort_by == "name_az":
        return sorted(products, key=lambda p: (p["name"] or "").lower())
    if sort_by == "name_za":
        return sorted(products, key=lambda p: (p["name"] or "").lower(), reverse=True)
    if sort_by == "newest":
        return sorted(products, key=lambda p: int(p["id"] or 0), reverse=True)
    return products


def fetch_products(filters=None):
    filters = filters or {}
    laptop_url = os.getenv("LAPTOP_SERVICE_URL", "http://laptop-service:8000")
    mobile_url = os.getenv("MOBILE_SERVICE_URL", "http://mobile-service:8000")
    accessory_url = os.getenv("ACCESSORY_SERVICE_URL", "http://accessory-service:8000")

    category = filters.get("category", "all")
    products = []
    if category in {"all", "laptop"}:
        products.extend(_fetch_service_products("laptop", laptop_url, filters))
    if category in {"all", "mobile"}:
        products.extend(_fetch_service_products("mobile", mobile_url, filters))
    if category in {"all", "accessory"}:
        products.extend(_fetch_service_products("accessory", accessory_url, filters))

    sort_by = filters.get("sort", "newest")
    products = _sort_products(products, sort_by)

    # Defensive parsing in case any service returns malformed price values.
    for product in products:
        try:
            product["price_number"] = Decimal(str(product["price"]))
        except (InvalidOperation, TypeError, ValueError):
            product["price_number"] = Decimal("0")

    return products


def get_available_brands(products):
    brands = sorted({(p.get("brand") or "").strip() for p in products if (p.get("brand") or "").strip()})
    return brands


def request_chatbot_reply(question, current_product=None, user_context=None, user_ref="", limit=5):
    base_url = (os.getenv("CHATBOT_SERVICE_URL") or "http://chatbot-service:8000").rstrip("/")
    request_timeout = max(10, int(os.getenv("CHATBOT_REQUEST_TIMEOUT_SECONDS", "40") or "40"))
    retry_on_timeout = max(1, int(os.getenv("CHATBOT_REQUEST_RETRIES", "2") or "2"))

    if base_url.endswith("/api/chat/reply"):
        endpoint = f"{base_url}/"
    else:
        endpoint = f"{base_url}/api/chat/reply/"

    payload = {
        "message": (question or "").strip(),
        "current_product": current_product or None,
        "user_context": user_context or {},
        "user_ref": str(user_ref or "").strip(),
        "limit": max(1, int(limit or 5)),
    }

    response = None
    data = {}
    for attempt in range(retry_on_timeout):
        try:
            response = requests.post(endpoint, json=payload, timeout=request_timeout)
            data = response.json() if response.content else {}
            break
        except requests.ReadTimeout:
            if attempt + 1 >= retry_on_timeout:
                return {
                    "answer": "Chatbot service is temporarily unavailable. Please try again.",
                    "recommendations": [],
                    "citations": [],
                    "source": "chatbot_service_unavailable",
                    "fallback_used": True,
                    "error_code": "service_timeout",
                }
        except ValueError:
            return {
                "answer": "Chatbot service returned an invalid response.",
                "recommendations": [],
                "citations": [],
                "source": "chatbot_service_error",
                "fallback_used": True,
                "error_code": "invalid_response",
            }
        except requests.RequestException:
            return {
                "answer": "Chatbot service is temporarily unavailable. Please try again.",
                "recommendations": [],
                "citations": [],
                "source": "chatbot_service_unavailable",
                "fallback_used": True,
                "error_code": "service_unavailable",
            }

    if response is None:
        return {
            "answer": "Chatbot service is temporarily unavailable. Please try again.",
            "recommendations": [],
            "citations": [],
            "source": "chatbot_service_unavailable",
            "fallback_used": True,
            "error_code": "service_unavailable",
        }

    if not response.ok:
        return {
            "answer": (data or {}).get("error") or "Chatbot service could not process your request.",
            "recommendations": [],
            "citations": [],
            "source": "chatbot_service_error",
            "fallback_used": True,
            "error_code": "upstream_error",
        }

    if not isinstance(data, dict):
        data = {}

    return {
        "answer": data.get("answer") or "No response generated.",
        "recommendations": data.get("recommendations") or [],
        "citations": data.get("citations") or [],
        "source": data.get("source") or "chatbot_service",
        "fallback_used": bool(data.get("fallback_used")),
        "error_code": data.get("error_code"),
        "provider": data.get("provider"),
    }


def fetch_product_detail(service_name, product_id):
    laptop_url = os.getenv("LAPTOP_SERVICE_URL", "http://laptop-service:8000")
    mobile_url = os.getenv("MOBILE_SERVICE_URL", "http://mobile-service:8000")
    accessory_url = os.getenv("ACCESSORY_SERVICE_URL", "http://accessory-service:8000")

    if service_name == "laptop":
        base_url = laptop_url
    elif service_name == "mobile":
        base_url = mobile_url
    elif service_name == "accessory":
        base_url = accessory_url
    else:
        return None

    try:
        response = requests.get(f"{base_url}/api/products/{product_id}/", timeout=6)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return None

    return {
        "service": service_name,
        "id": payload.get("id"),
        "name": payload.get("name", "N/A"),
        "description": payload.get("description", ""),
        "image_url": payload.get("image_url", ""),
        "brand": payload.get("brand", ""),
        "price": payload.get("price", "0"),
        "stock": payload.get("stock", 0),
    }


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_decimal(value, default=Decimal("0")):
    try:
        return Decimal(str(value))
    except (TypeError, ValueError, InvalidOperation):
        return default


def _tokenize(text):
    lowered = (text or "").lower()
    return [token for token in re.findall(r"[a-z0-9]+", lowered) if len(token) > 1]


def _unique_products(products):
    seen = set()
    unique_items = []
    for item in products:
        service = (item.get("service") or "").strip().lower()
        product_id = _to_int(item.get("id"), 0)
        if not service or product_id <= 0:
            continue
        key = (service, product_id)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)
    return unique_items


def _normalize_product(item):
    return {
        "service": item.get("service"),
        "id": _to_int(item.get("id"), 0),
        "name": item.get("name") or "N/A",
        "brand": item.get("brand") or "",
        "description": item.get("description") or "",
        "price": str(item.get("price") or "0"),
        "stock": _to_int(item.get("stock"), 0),
        "image_url": item.get("image_url") or "",
    }


def _detail_recommendation_score(product, current_product, cart_service_counts):
    score = Decimal("0")

    service = (product.get("service") or "").strip().lower()
    stock = _to_int(product.get("stock"), 0)
    if stock > 0:
        score += Decimal("4")
    else:
        score -= Decimal("5")

    if service == (current_product.get("service") or ""):
        score += Decimal("1.4")

    cart_weight = cart_service_counts.get(service, 0)
    if cart_weight >= 3:
        # Explicit threshold: strong priority when user already has >=3 items in same service.
        score += Decimal("5.5")
    elif cart_weight > 0:
        score += Decimal(str(min(cart_weight, 2))) * Decimal("1.2")

    current_brand = str(current_product.get("brand") or "").strip().lower()
    product_brand = str(product.get("brand") or "").strip().lower()
    if current_brand and product_brand and current_brand == product_brand:
        score += Decimal("2.2")

    current_price = _to_decimal(current_product.get("price"), Decimal("0"))
    product_price = _to_decimal(product.get("price"), Decimal("0"))
    if current_price > 0 and product_price > 0:
        delta_ratio = abs(product_price - current_price) / current_price
        if delta_ratio <= Decimal("0.12"):
            score += Decimal("1.5")
        elif delta_ratio <= Decimal("0.30"):
            score += Decimal("0.8")

    base_tokens = _tokenize(
        " ".join(
            [
                str(current_product.get("name") or ""),
                str(current_product.get("brand") or ""),
                str(current_product.get("description") or ""),
            ]
        )
    )
    haystack = " ".join(
        [
            str(product.get("name") or "").lower(),
            str(product.get("brand") or "").lower(),
            str(product.get("description") or "").lower(),
        ]
    )
    token_hits = sum(1 for token in base_tokens[:6] if token in haystack)
    score += Decimal(min(token_hits, 4)) * Decimal("0.5")

    return score


def _target_mix_by_service(limit, cart_service_counts):
    services = ["laptop", "mobile", "accessory"]
    if limit <= 0:
        return {service: 0 for service in services}

    mix = {"laptop": 2, "mobile": 2, "accessory": 2}
    if limit != 6:
        base = limit // 3
        rem = limit % 3
        mix = {service: base for service in services}
        for service in services[:rem]:
            mix[service] += 1

    preferred_service = None
    preferred_score = 0
    for service in services:
        current = cart_service_counts.get(service, 0)
        if current > preferred_score:
            preferred_service = service
            preferred_score = current

    if preferred_service and preferred_score >= 3 and limit >= 4:
        mix = {"laptop": 1, "mobile": 1, "accessory": 1}
        mix[preferred_service] = min(3, limit - 2)
        remaining = limit - mix[preferred_service]
        other_services = [service for service in services if service != preferred_service]
        mix[other_services[0]] = remaining // 2
        mix[other_services[1]] = remaining - mix[other_services[0]]

    return mix


def recommend_products_for_detail(current_product, cart_items=None, limit=6, mode="mixed"):
    current_product = current_product or {}
    cart_items = cart_items or []
    mode = (mode or "mixed").strip().lower()
    if mode not in {"mixed", "similar"}:
        mode = "mixed"

    default_filters = {
        "q": "",
        "category": "all",
        "stock": "all",
        "price_range": "all",
        "sort": "newest",
        "brand": "all",
    }
    candidates = _unique_products(fetch_products(default_filters))
    if not candidates:
        return []

    current_service = (current_product.get("service") or "").strip().lower()
    current_id = _to_int(current_product.get("id"), 0)
    candidates = [
        item
        for item in candidates
        if not (
            (item.get("service") or "").strip().lower() == current_service
            and _to_int(item.get("id"), 0) == current_id
        )
    ]

    if mode == "similar" and current_service in {"laptop", "mobile", "accessory"}:
        same_service = [
            item for item in candidates if (item.get("service") or "").strip().lower() == current_service
        ]
        if same_service:
            candidates = same_service

    cart_service_counts = {"laptop": 0, "mobile": 0, "accessory": 0}
    for item in cart_items:
        service = (item.get("product_service") or "").strip().lower()
        if service in cart_service_counts:
            cart_service_counts[service] += _to_int(item.get("quantity"), 0) or 1

    ranked = []
    for item in candidates:
        score = _detail_recommendation_score(item, current_product, cart_service_counts)
        ranked.append((score, _to_int(item.get("stock"), 0), _to_int(item.get("id"), 0), item))

    ranked.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    bucket = {"laptop": [], "mobile": [], "accessory": []}
    for row in ranked:
        service = (row[3].get("service") or "").strip().lower()
        if service in bucket:
            bucket[service].append(row[3])

    selected = []
    selected_keys = set()

    if mode == "mixed":
        target_mix = _target_mix_by_service(max(1, limit), cart_service_counts)

        for service_name in ["laptop", "mobile", "accessory"]:
            target = target_mix.get(service_name, 0)
            for product in bucket.get(service_name, []):
                if len(selected) >= limit or target <= 0:
                    break
                key = (service_name, _to_int(product.get("id"), 0))
                if key in selected_keys:
                    continue
                selected_keys.add(key)
                selected.append(product)
                target -= 1

        if len(selected) < limit:
            for _, _, _, product in ranked:
                service = (product.get("service") or "").strip().lower()
                key = (service, _to_int(product.get("id"), 0))
                if key in selected_keys:
                    continue
                selected_keys.add(key)
                selected.append(product)
                if len(selected) >= limit:
                    break
    else:
        for _, _, _, product in ranked:
            service = (product.get("service") or "").strip().lower()
            key = (service, _to_int(product.get("id"), 0))
            if key in selected_keys:
                continue
            selected_keys.add(key)
            selected.append(product)
            if len(selected) >= limit:
                break

    return [_normalize_product(item) for item in selected[:limit]]
