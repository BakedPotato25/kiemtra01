import os


def _rstrip_slash(value):
    return (value or "").rstrip("/")


def build_gateway_registry(request=None):
    customer_public_base = "http://localhost:8000"
    if request is not None:
        customer_public_base = _rstrip_slash(request.build_absolute_uri("/"))

    localhost_services = {
        "customer_service": "http://localhost:8000",
        "staff_service": "http://localhost:8003",
        "laptop_service": "http://localhost:8001",
        "mobile_service": "http://localhost:8002",
        "accessory_service": "http://localhost:8004",
        "chatbot_service": "http://localhost:8005",
    }

    internal_services = {
        "customer_service": customer_public_base,
        "staff_service": _rstrip_slash(os.getenv("STAFF_SERVICE_URL") or "http://staff-service:8000"),
        "laptop_service": _rstrip_slash(os.getenv("LAPTOP_SERVICE_URL") or "http://laptop-service:8000"),
        "mobile_service": _rstrip_slash(os.getenv("MOBILE_SERVICE_URL") or "http://mobile-service:8000"),
        "accessory_service": _rstrip_slash(os.getenv("ACCESSORY_SERVICE_URL") or "http://accessory-service:8000"),
        "chatbot_service": _rstrip_slash(os.getenv("CHATBOT_SERVICE_URL") or "http://chatbot-service:8000"),
    }

    routes = [
        {
            "gateway": "customer_service",
            "public_path": "/customer/chatbot/reply/",
            "public_url": f"{customer_public_base}/customer/chatbot/reply/",
            "method": "POST",
            "upstream": "chatbot_service",
            "upstream_urls": [f"{internal_services['chatbot_service']}/api/chat/reply/"],
            "description": "Forward chat requests to chatbot microservice.",
        },
        {
            "gateway": "customer_service",
            "public_path": "/customer/dashboard/",
            "public_url": f"{customer_public_base}/customer/dashboard/",
            "method": "GET",
            "upstream": "catalog_services",
            "upstream_urls": [
                f"{internal_services['laptop_service']}/api/products/",
                f"{internal_services['mobile_service']}/api/products/",
                f"{internal_services['accessory_service']}/api/products/",
            ],
            "description": "Aggregate product feeds from laptop/mobile/accessory services.",
        },
        {
            "gateway": "customer_service",
            "public_path": "/customer/products/{service}/{id}/",
            "public_url": f"{customer_public_base}/customer/products/{{service}}/{{id}}/",
            "method": "GET",
            "upstream": "catalog_service_by_category",
            "upstream_urls": [
                "{LAPTOP|MOBILE|ACCESSORY}_SERVICE_URL/api/products/{id}/",
            ],
            "description": "Load product detail from matching catalog service.",
        },
        {
            "gateway": "staff_service",
            "public_path": "/staff/items/",
            "public_url": f"{localhost_services['staff_service']}/staff/items/",
            "method": "GET/POST/PUT/DELETE",
            "upstream": "catalog_services",
            "upstream_urls": [
                f"{internal_services['laptop_service']}/api/products/",
                f"{internal_services['mobile_service']}/api/products/",
                f"{internal_services['accessory_service']}/api/products/",
                "{SERVICE_URL}/api/products/{id}/",
            ],
            "description": "Staff gateway to list/create/update/delete products via catalog APIs.",
        },
        {
            "gateway": "staff_service",
            "public_path": "/staff/customers/",
            "public_url": f"{localhost_services['staff_service']}/staff/customers/",
            "method": "GET",
            "upstream": "customer_service",
            "upstream_urls": [f"{customer_public_base}/customer/staff/analytics/"],
            "description": "Staff analytics via customer service bridge endpoint.",
        },
    ]

    return {
        "message": "Gateway API index",
        "gateway_index_url": f"{customer_public_base}/gateway/apis/",
        "gateway_dashboard_url": f"{customer_public_base}/gateway/",
        "services": {
            name: {
                "localhost": localhost_services[name],
                "internal": internal_services[name],
            }
            for name in localhost_services
        },
        "routes": routes,
    }
