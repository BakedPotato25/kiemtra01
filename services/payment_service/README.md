# payment_service

`payment_service` owns internal payment records for orders. It stores order and user references, amount, payment status, timestamps, and paid-at state.

## Runtime

- Compose service: `payment_service`
- Docker hostname: `payment-service`
- Host port: internal-only
- Public gateway path: `/api/payments/`
- Database: PostgreSQL `payment_db`

## Key Routes

- `POST /api/payments/`
- `GET /api/payments/<payment_id>/`
- `GET /api/payments/by-order/<order_id>/`
- `POST /api/payments/<payment_id>/confirm/`
- `POST /api/payments/<payment_id>/cancel/`

All endpoints require `X-Internal-Key` matching `PAYMENT_SERVICE_INTERNAL_KEY`.

## Commands

```bash
python bootstrap_postgres.py
python manage.py migrate
python manage.py test payments
```

