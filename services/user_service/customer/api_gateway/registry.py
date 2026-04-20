import os


def _rstrip_slash(value):
    return (value or "").rstrip("/")


def build_gateway_registry(request=None):
    user_public_base = "http://localhost:8000"
    if request is not None:
        user_public_base = _rstrip_slash(request.build_absolute_uri("/"))

    localhost_services = {
        "user_service": "http://localhost:8000",
        "product_service": "http://localhost:8001",
        "order_service": "internal-only",
        "chatbot_service": "http://localhost:8005",
    }
    internal_services = {
        "user_service": user_public_base,
        "product_service": _rstrip_slash(os.getenv("PRODUCT_SERVICE_URL") or "http://product-service:8000"),
        "order_service": _rstrip_slash(os.getenv("ORDER_SERVICE_URL") or "http://order-service:8000"),
        "chatbot_service": _rstrip_slash(os.getenv("CHATBOT_SERVICE_URL") or "http://chatbot-service:8000"),
    }
    routes = [
        {
            "gateway": "user_service",
            "public_path": "/customer/dashboard/",
            "public_url": f"{user_public_base}/customer/dashboard/",
            "method": "GET",
            "upstream": "product_service",
            "upstream_urls": [f"{internal_services['product_service']}/api/products/"],
            "description": "Aggregate the unified product catalog for storefront browsing.",
        },
        {
            "gateway": "user_service",
            "public_path": "/customer/products/{category_slug}/{id}/",
            "public_url": f"{user_public_base}/customer/products/{{category_slug}}/{{id}}/",
            "method": "GET",
            "upstream": "product_service",
            "upstream_urls": [f"{internal_services['product_service']}/api/products/{{id}}/"],
            "description": "Load a single product from the unified catalog service.",
        },
        {
            "gateway": "user_service",
            "public_path": "/customer/cart/ + /customer/orders/",
            "public_url": f"{user_public_base}/customer/cart/",
            "method": "GET/POST",
            "upstream": "order_service",
            "upstream_urls": [
                f"{internal_services['order_service']}/api/cart/",
                f"{internal_services['order_service']}/api/orders/",
                f"{internal_services['order_service']}/api/checkout/",
            ],
            "description": "Persist cart, saved, compare, checkout, and orders via order_service.",
        },
        {
            "gateway": "user_service",
            "public_path": "/customer/chatbot/reply/",
            "public_url": f"{user_public_base}/customer/chatbot/reply/",
            "method": "POST",
            "upstream": "chatbot_service",
            "upstream_urls": [f"{internal_services['chatbot_service']}/api/chat/reply/"],
            "description": "Forward customer chat requests to chatbot_service.",
        },
    ]

    return {
        "message": "Gateway API index",
        "gateway_index_url": f"{user_public_base}/gateway/apis/",
        "gateway_dashboard_url": f"{user_public_base}/gateway/",
        "services": {
            name: {
                "localhost": localhost_services[name],
                "internal": internal_services[name],
            }
            for name in localhost_services
        },
        "routes": routes,
    }
