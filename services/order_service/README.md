# order_service

`order_service` owns commerce state outside the UI: cart items, saved items, compare items, checkout, order history, order item snapshots, payment/shipping snapshots, customer analytics, behavior-source export, and legacy order import.

## Runtime

- Compose service: `order_service`
- Docker hostname: `order-service`
- Host port: internal-only
- Public gateway paths: `/api/cart/`, `/api/saved/`, `/api/compare/`, `/api/checkout/`, `/api/orders/`, `/api/staff/orders/`, `/api/analytics/`, `/api/internal/`
- Database: MySQL `order_db`

## Key Routes

- Cart: `/api/cart/`, `/api/cart/<item_id>/`
- Saved: `/api/saved/`, `/api/saved/toggle/`
- Compare: `/api/compare/`, `/api/compare/toggle/`, `/api/compare/<item_id>/`
- Checkout/orders: `/api/checkout/`, `/api/orders/`, `/api/orders/<order_id>/pay/`
- Staff shipping: `/api/staff/orders/`, `/api/staff/orders/<order_id>/shipping/`
- Analytics and behavior export: `/api/analytics/customers/`, `/api/internal/behavior-source/`

All endpoints require `X-Internal-Key` matching `ORDER_SERVICE_INTERNAL_KEY`.

## Downstream Services

Checkout creates pending records in `payment_service` and `shipping_service`. Pay-order confirms through `payment_service`; staff shipping updates go through `shipping_service` and then sync the order snapshot.

## Commands

```bash
python bootstrap_mysql.py
python manage.py migrate
python manage.py import_legacy_orders
python manage.py test orders
```

