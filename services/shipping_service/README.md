# shipping_service

`shipping_service` owns internal shipment records for orders. It stores order and user references, recipient address snapshots, shipment status, and lifecycle timestamps.

## Runtime

- Compose service: `shipping_service`
- Docker hostname: `shipping-service`
- Host port: internal-only
- Public gateway path: `/api/shipments/`
- Database: PostgreSQL `shipping_db`

## Key Routes

- `POST /api/shipments/`
- `GET /api/shipments/<shipment_id>/`
- `GET /api/shipments/by-order/<order_id>/`
- `PATCH /api/shipments/<shipment_id>/status/`
- `POST /api/shipments/<shipment_id>/status/`

All endpoints require `X-Internal-Key` matching `SHIPPING_SERVICE_INTERNAL_KEY`.

## Status Flow

Supported statuses are `pending`, `preparing`, `shipped`, `delivered`, and `cancelled`. Terminal and backward transitions are rejected by the service rules.

## Commands

```bash
python bootstrap_postgres.py
python manage.py migrate
python manage.py test shipments
```

