import os
import random

import requests
from django.core.management.base import BaseCommand

from customer.models import CartItem, Order, OrderItem, SavedItem


def _build_message(item, rng):
    service = (item.product_service or "product").strip().lower()
    product_name = (item.product_name or "this product").strip()
    brand = (item.product_brand or "").strip()
    price = str(item.unit_price)

    service_phrase = {
        "laptop": "laptop",
        "mobile": "phone",
        "accessory": "accessory",
    }.get(service, "product")

    templates = [
        "I bought {name}. Suggest similar {service} options in my price range around ${price}.",
        "Please recommend better alternatives to {name} ({brand}) with good value.",
        "I am interested in {service} products like {name}. What should I check next?",
        "Based on my purchase history, suggest practical {service} products related to {name}.",
    ]
    template = rng.choice(templates)
    return template.format(
        name=product_name,
        service=service_phrase,
        brand=brand or "N/A",
        price=price,
    )


def _append_limited(bucket, user_id, value, limit=8):
    if not value:
        return
    current = bucket.setdefault(user_id, [])
    if len(current) >= limit:
        return
    current.append(value)


class Command(BaseCommand):
    help = "Backfill chatbot behavior events from real customer orders/cart/saved data"

    def add_arguments(self, parser):
        parser.add_argument("--max-events", type=int, default=1200, help="Maximum events to ingest")
        parser.add_argument("--max-users", type=int, default=300, help="Maximum users to include")
        parser.add_argument(
            "--source-status",
            choices=["paid", "all"],
            default="paid",
            help="Order status source used for backfill",
        )
        parser.add_argument("--seed", type=int, default=20260407, help="Random seed for template selection")
        parser.add_argument("--timeout", type=int, default=8, help="Request timeout in seconds")
        parser.add_argument("--dry-run", action="store_true", help="Preview without sending to chatbot service")

    def handle(self, *args, **options):
        max_events = max(1, int(options["max_events"]))
        max_users = max(1, int(options["max_users"]))
        source_status = options["source_status"]
        timeout_seconds = max(3, int(options["timeout"]))
        dry_run = bool(options["dry_run"])
        rng = random.Random(int(options["seed"]))

        base_url = (os.getenv("CHATBOT_SERVICE_URL") or "http://chatbot-service:8000").rstrip("/")
        if base_url.endswith("/api/chat/reply"):
            base_url = base_url[: -len("/api/chat/reply")]
        ingest_endpoint = f"{base_url}/api/chat/ingest-behavior/"

        ingest_key = (os.getenv("CHATBOT_INGEST_KEY") or "").strip()
        headers = {}
        if ingest_key:
            headers["X-Ingest-Key"] = ingest_key

        order_qs = Order.objects.all().order_by("-created_at")
        if source_status == "paid":
            order_qs = order_qs.filter(status=Order.STATUS_PAID)

        user_ids = list(order_qs.values_list("user_id", flat=True).distinct()[:max_users])
        if not user_ids:
            self.stdout.write(self.style.WARNING("No source users found from order history."))
            return

        carts_by_user = {}
        for row in CartItem.objects.filter(user_id__in=user_ids).order_by("-updated_at"):
            _append_limited(carts_by_user, row.user_id, row.product_name)

        saved_by_user = {}
        for row in SavedItem.objects.filter(user_id__in=user_ids).order_by("-created_at"):
            _append_limited(saved_by_user, row.user_id, row.product_name)

        paid_recent_by_user = {}
        recent_paid_rows = (
            OrderItem.objects.filter(order__user_id__in=user_ids, order__status=Order.STATUS_PAID)
            .select_related("order")
            .order_by("-order__created_at", "-order_id")
        )
        for row in recent_paid_rows:
            _append_limited(paid_recent_by_user, row.order.user_id, row.product_name)

        source_orders = list(order_qs.filter(user_id__in=user_ids).prefetch_related("items"))
        if not source_orders:
            self.stdout.write(self.style.WARNING("No source orders found after filtering."))
            return

        sent = 0
        succeeded = 0
        failed = 0
        sample_errors = []

        for order in source_orders:
            for item in order.items.all():
                if sent >= max_events:
                    break

                user_ref = str(order.user_id)
                user_context = {
                    "cart_items": carts_by_user.get(order.user_id, []),
                    "saved_items": saved_by_user.get(order.user_id, []),
                    "recent_paid_items": paid_recent_by_user.get(order.user_id, []),
                }
                current_product = {
                    "service": (item.product_service or "").strip().lower(),
                    "id": int(item.product_id or 0),
                    "name": item.product_name or "",
                    "brand": item.product_brand or "",
                    "price": str(item.unit_price),
                }
                payload = {
                    "message": _build_message(item, rng),
                    "current_product": current_product,
                    "user_context": user_context,
                    "user_ref": user_ref,
                }

                sent += 1
                if dry_run:
                    succeeded += 1
                    continue

                try:
                    response = requests.post(
                        ingest_endpoint,
                        json=payload,
                        headers=headers,
                        timeout=timeout_seconds,
                    )
                except requests.RequestException as exc:
                    failed += 1
                    if len(sample_errors) < 5:
                        sample_errors.append(f"request_error: {exc}")
                    continue

                if response.ok:
                    succeeded += 1
                else:
                    failed += 1
                    if len(sample_errors) < 5:
                        sample_errors.append(f"http_{response.status_code}: {response.text[:160]}")

            if sent >= max_events:
                break

        mode = "DRY-RUN" if dry_run else "LIVE"
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill ({mode}) finished. users={len(user_ids)} sent={sent} success={succeeded} failed={failed} endpoint={ingest_endpoint}"
            )
        )
        for err in sample_errors:
            self.stdout.write(self.style.WARNING(f"sample_error: {err}"))
