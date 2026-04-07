import os
import re
from decimal import Decimal, InvalidOperation

import requests

from .content import FAQ_ITEMS


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


def _looks_vietnamese(text):
    lowered = (text or "").lower()
    if any(char in lowered for char in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"):
        return True
    vi_keywords = ["toi", "goi y", "san pham", "dien thoai", "laptop", "phu kien", "gia", "duoi", "tren"]
    return any(keyword in lowered for keyword in vi_keywords)


def _asks_for_in_stock_only(text):
    lowered = (text or "").lower()
    stock_keywords = [
        "con hang",
        "còn hàng",
        "ton kho",
        "tồn kho",
        "co san",
        "có sẵn",
        "in stock",
        "available",
        "availability",
    ]
    return any(keyword in lowered for keyword in stock_keywords)


def _detect_requested_services(text):
    lowered = (text or "").lower()
    keyword_map = {
        "mobile": [
            "mobile",
            "phone",
            "smartphone",
            "dien thoai",
            "điện thoại",
            "ios",
            "android",
        ],
        "laptop": ["laptop", "notebook", "ultrabook", "macbook"],
        "accessory": [
            "accessory",
            "accessories",
            "phu kien",
            "phụ kiện",
            "tai nghe",
            "headphone",
            "charger",
            "sac",
            "sạc",
            "keyboard",
            "mouse",
            "cable",
            "cap",
            "cáp",
        ],
    }

    matches = []
    for service_name, keywords in keyword_map.items():
        if any(keyword in lowered for keyword in keywords):
            matches.append(service_name)
    return matches


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


def _candidate_pool(question, current_product, target_services=None):
    target_services = [service for service in (target_services or []) if service in {"laptop", "mobile", "accessory"}]
    default_filters = {
        "q": "",
        "category": "all",
        "stock": "all",
        "price_range": "all",
        "sort": "newest",
        "brand": "all",
    }

    pool = []
    if target_services:
        for service_name in target_services:
            query_filters = dict(default_filters)
            query_filters["q"] = question
            query_filters["category"] = service_name
            pool.extend(fetch_products(query_filters))
    else:
        query_filters = dict(default_filters)
        query_filters["q"] = question
        pool = fetch_products(query_filters)

    current_service = (current_product or {}).get("service")
    if current_service in {"laptop", "mobile", "accessory"} and current_service not in target_services:
        related_filters = dict(default_filters)
        related_filters["category"] = current_service
        pool.extend(fetch_products(related_filters))

    if len(pool) < 20:
        if target_services:
            for service_name in target_services:
                backup_filters = dict(default_filters)
                backup_filters["category"] = service_name
                pool.extend(fetch_products(backup_filters))
        else:
            pool.extend(fetch_products(default_filters))

    return _unique_products(pool)


def _score_product(product, question_tokens, current_product):
    score = Decimal("0")

    stock = _to_int(product.get("stock"), 0)
    if stock > 0:
        score += Decimal("2")
    else:
        score -= Decimal("4")

    haystack = " ".join(
        [
            str(product.get("name") or "").lower(),
            str(product.get("brand") or "").lower(),
            str(product.get("description") or "").lower(),
        ]
    )
    token_hits = sum(1 for token in question_tokens if token in haystack)
    score += Decimal(min(token_hits, 5))

    if current_product:
        if product.get("service") == current_product.get("service"):
            score += Decimal("4")

        current_brand = str(current_product.get("brand") or "").strip().lower()
        product_brand = str(product.get("brand") or "").strip().lower()
        if current_brand and product_brand and current_brand == product_brand:
            score += Decimal("3")

        current_price = _to_decimal(current_product.get("price"), Decimal("0"))
        product_price = _to_decimal(product.get("price"), Decimal("0"))
        if current_price > 0 and product_price > 0:
            delta_ratio = abs(product_price - current_price) / current_price
            if delta_ratio <= Decimal("0.10"):
                score += Decimal("2")
            elif delta_ratio <= Decimal("0.25"):
                score += Decimal("1")

        if (
            _to_int(product.get("id"), 0) == _to_int(current_product.get("id"), -1)
            and product.get("service") == current_product.get("service")
        ):
            score -= Decimal("99")

    return score


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


def recommend_products_for_chat(question, current_product=None, limit=5):
    target_services = _detect_requested_services(question)
    candidates = _candidate_pool(question, current_product, target_services=target_services)
    if not candidates:
        return []

    if _asks_for_in_stock_only(question):
        in_stock_candidates = [item for item in candidates if _to_int(item.get("stock"), 0) > 0]
        if in_stock_candidates:
            candidates = in_stock_candidates

    tokens = _tokenize(question)
    ranked = []
    for product in candidates:
        score = _score_product(product, tokens, current_product)
        service = (product.get("service") or "").strip().lower()
        if target_services:
            if service in target_services:
                score += Decimal("2.6")
            else:
                score -= Decimal("2.2")
        ranked.append(
            (
                score,
                _to_int(product.get("stock"), 0),
                _to_int(product.get("id"), 0),
                product,
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)

    if target_services:
        scoped_rows = [row for row in ranked if (row[3].get("service") or "").strip().lower() in target_services]
        spill_rows = [row for row in ranked if row not in scoped_rows]
        ordered_rows = scoped_rows + spill_rows
    else:
        ordered_rows = ranked

    top_items = [item[3] for item in ordered_rows[: max(1, limit)]]

    return [_normalize_product(item) for item in top_items]


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


def _recent_blog_context(limit=2):
    try:
        from .models import BlogPost

        posts = BlogPost.objects.order_by("-published_at", "-id")[:limit]
        return [f"{post.title}: {post.excerpt}" for post in posts]
    except Exception:
        return []


def _recent_blog_titles(limit=2):
    try:
        from .models import BlogPost

        posts = BlogPost.objects.order_by("-published_at", "-id")[:limit]
        return [post.title for post in posts]
    except Exception:
        return []


def _build_citations(recommendations, current_product=None):
    citations = []

    for item in recommendations[:3]:
        service = (item.get("service") or "").strip().lower()
        product_id = _to_int(item.get("id"), 0)
        if service in {"laptop", "mobile", "accessory"} and product_id > 0:
            citations.append(
                {
                    "label": "Product catalog",
                    "detail": f"[{service}] {item.get('name') or 'N/A'}",
                    "url": f"/customer/products/{service}/{product_id}/",
                }
            )

    if citations:
        return citations[:3]

    if current_product and current_product.get("service") and _to_int(current_product.get("id"), 0) > 0:
        service = current_product.get("service")
        product_id = _to_int(current_product.get("id"), 0)
        citations.append(
            {
                "label": "Current product context",
                "detail": f"[{service}] {current_product.get('name') or 'N/A'}",
                "url": f"/customer/products/{service}/{product_id}/",
            }
        )

    if len(citations) < 3 and FAQ_ITEMS:
        citations.append(
            {
                "label": "FAQ",
                "detail": FAQ_ITEMS[0].get("question") or "FAQ item",
                "url": "/customer/dashboard/#section-faq",
            }
        )

    deduped = []
    seen = set()
    for citation in citations:
        key = ((citation.get("label") or "").strip().lower(), (citation.get("detail") or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
        if len(deduped) >= 3:
            break

    return deduped


def _answer_with_citations(answer, citations, language):
    return (answer or "").strip()


def _build_prompt(question, recommendations, user_context, language, target_services=None):
    target_services = target_services or []
    faq_lines = [f"- {item['question']}: {item['answer']}" for item in FAQ_ITEMS[:3]]
    blog_lines = [f"- {line}" for line in _recent_blog_context(limit=2)]
    rec_lines = [
        f"- [{item['service']}] {item['name']} | brand={item.get('brand') or 'N/A'} | price=${item['price']} | stock={item['stock']}"
        for item in recommendations[:5]
    ]

    profile_parts = []
    cart = user_context.get("cart_items") or []
    saved = user_context.get("saved_items") or []
    bought = user_context.get("recent_paid_items") or []
    if cart:
        profile_parts.append("cart=" + ", ".join(cart[:4]))
    if saved:
        profile_parts.append("saved=" + ", ".join(saved[:4]))
    if bought:
        profile_parts.append("recent_paid=" + ", ".join(bought[:4]))
    profile_text = "; ".join(profile_parts) if profile_parts else "no user profile signal"

    if target_services:
        if language == "vi":
            focus_line = "Danh muc duoc yeu cau: " + ", ".join(target_services)
        else:
            focus_line = "Requested category focus: " + ", ".join(target_services)
    else:
        focus_line = "Requested category focus: none"

    target_language = "Vietnamese" if language == "vi" else "English"
    return (
        "You are a shopping assistant for a multi-category electronics store. "
        "Give a complete and practical answer grounded in context. "
        "When user asks a specific category, keep recommendations in that category unless user asks cross-category. "
        "Do not include a Sources/Citations section in your answer. "
        f"Respond in {target_language}.\n\n"
        f"User question: {question}\n\n"
        f"User profile signals: {profile_text}\n\n"
        f"{focus_line}\n\n"
        "Top recommendation candidates:\n"
        + ("\n".join(rec_lines) if rec_lines else "- No candidate products available")
        + "\n\nFAQ snippets:\n"
        + ("\n".join(faq_lines) if faq_lines else "- No FAQ")
        + "\n\nRecent blog snippets:\n"
        + ("\n".join(blog_lines) if blog_lines else "- No blog")
        + "\n\n"
        "Output style:\n"
        "1) Start with 3-5 complete sentences that directly answer the question.\n"
        "2) Then provide 3-5 bullets in format: - ProductName (service, brand, price, stock).\n"
        "3) If stock-only intent appears, prioritize in-stock products only."
    )


def _call_gemini(prompt_text):
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return None, "missing_api_key"

    model_name = (os.getenv("GEMINI_MODEL") or "gemini-3-flash-preview").strip()
    if model_name.startswith("models/"):
        model_name = model_name.split("/", 1)[1]
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    params = {"key": api_key}

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 560,
        },
    }

    try:
        response = requests.post(endpoint, params=params, json=payload, timeout=12)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None, "network_error"
    except ValueError:
        return None, "invalid_response"

    candidates = data.get("candidates") or []
    if not candidates:
        return None, "empty_candidates"

    parts = (candidates[0].get("content") or {}).get("parts") or []
    text_chunks = [part.get("text", "") for part in parts if part.get("text")]
    answer = "\n".join(chunk.strip() for chunk in text_chunks if chunk.strip()).strip()
    if not answer:
        return None, "empty_text"
    return answer, None


def _fallback_answer(question, recommendations, language):
    if language == "vi":
        head = "Minh dang dung che do fallback (khong goi duoc LLM), nhung van co goi y nhanh cho ban."
        if recommendations:
            lines = [
                f"- {item['name']} ({item['service']}, {item.get('brand') or 'N/A'}, ${item['price']}, ton kho {item['stock']})"
                for item in recommendations[:5]
            ]
            return head + "\n\n" + "Goi y phu hop:\n" + "\n".join(lines)
        return head + "\n\nHien tai chua tim thay san pham phu hop. Ban thu mo ta ro hon nhu cau va tam gia giup minh."

    head = "I am using fallback mode right now (LLM unavailable), but I can still suggest products."
    if recommendations:
        lines = [
            f"- {item['name']} ({item['service']}, {item.get('brand') or 'N/A'}, ${item['price']}, stock {item['stock']})"
            for item in recommendations[:5]
        ]
        return head + "\n\nRecommended options:\n" + "\n".join(lines)
    return head + "\n\nI could not find a good match yet. Try adding category or budget details."


def _ensure_answer_detail(answer, recommendations, language):
    answer_text = (answer or "").strip()
    word_count = len(re.findall(r"\w+", answer_text))
    punctuation_endings = (".", "!", "?", "…")
    seems_incomplete = bool(answer_text) and not answer_text.endswith(punctuation_endings)
    if word_count >= 35 and not seems_incomplete:
        return answer_text

    if answer_text and seems_incomplete:
        answer_text = answer_text.rstrip() + "."

    if word_count < 20:
        if language == "vi":
            answer_text = (
                "Mình đã lọc nhanh theo nhu cầu của bạn, ưu tiên đúng danh mục, mức giá phù hợp và sản phẩm còn hàng."
            )
        else:
            answer_text = (
                "I filtered options for your request, prioritizing the right category, suitable pricing, and in-stock products."
            )

    if language == "vi":
        prefix = "Mình bổ sung nhanh để bạn dễ chọn hơn:"
        bullet_title = "Gợi ý nên xem:"
        stock_label = "ton kho"
    else:
        prefix = "Here is a fuller answer to make the choice easier:"
        bullet_title = "Suggested picks:"
        stock_label = "stock"

    lines = []
    for item in recommendations[:4]:
        lines.append(
            f"- {item['name']} ({item['service']}, {item.get('brand') or 'N/A'}, ${item['price']}, {stock_label} {item['stock']})"
        )

    if lines:
        return f"{answer_text}\n\n{prefix}\n{bullet_title}\n" + "\n".join(lines)
    return answer_text


def generate_chatbot_response(question, current_product=None, user_context=None, limit=5):
    user_context = user_context or {}
    current_product = current_product or None

    target_services = _detect_requested_services(question)
    recommendations = recommend_products_for_chat(
        question=question,
        current_product=current_product,
        limit=limit,
    )

    language = "vi" if _looks_vietnamese(question) else "en"
    prompt_text = _build_prompt(
        question,
        recommendations,
        user_context,
        language,
        target_services=target_services,
    )
    llm_answer, error_code = _call_gemini(prompt_text)

    if llm_answer:
        answer = _ensure_answer_detail(llm_answer, recommendations, language)
        source = "gemini"
        fallback_used = False
    else:
        answer = _fallback_answer(question, recommendations, language)
        source = "rule_based"
        fallback_used = True

    citations = _build_citations(recommendations, current_product=current_product)
    answer = _answer_with_citations(answer, citations, language)

    return {
        "answer": answer,
        "recommendations": recommendations,
        "citations": citations,
        "source": source,
        "fallback_used": fallback_used,
        "error_code": error_code,
    }
