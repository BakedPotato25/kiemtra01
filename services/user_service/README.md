# user_service

`user_service` is the browser-facing auth and UI edge behind the Nginx gateway. It owns customer UI, staff UI, Django admin, session auth, JWT auth, editorial content, gateway inspection views, chatbot proxying, and legacy user migration.

## Runtime

- Compose service: `user_service`
- Docker hostname: `user-service`
- Debug ports: `8000` and `8003`
- Public gateway paths: `/`, `/customer/`, `/staff/`, `/admin/`, `/gateway/`, `/api/auth/`
- Database: MySQL `user_db`

## API Gateway Location

There is no standalone Django service named `api_gateway`. The application-level gateway code lives here:

- `customer/api_gateway/definitions.py`
- `customer/api_gateway/registry.py`
- Gateway views in `customer/views.py`

Nginx remains the public reverse proxy in `docker/gateway/nginx.conf`; this service owns browser session orchestration and the `/gateway/` inspection UI.

## Key Routes

- Customer UI: `/customer/login/`, `/customer/register/`, `/customer/dashboard/`, `/customer/cart/`, `/customer/orders/`
- Customer chatbot proxy: `/customer/chatbot/reply/`
- Staff UI: `/staff/login/`, `/staff/register/`, `/staff/dashboard/`, `/staff/items/`, `/staff/customers/`, `/staff/orders/`
- JWT auth: `/api/auth/register/`, `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/me/`
- Gateway inspection: `/gateway/`, `/gateway/apis/`

## Dependencies

Runtime URLs are read from `PRODUCT_SERVICE_URL`, `ORDER_SERVICE_URL`, `PAYMENT_SERVICE_URL`, `SHIPPING_SERVICE_URL`, and `CHATBOT_SERVICE_URL`. Calls to `order_service` must include `ORDER_SERVICE_INTERNAL_KEY`.

## Commands

```bash
python bootstrap_mysql.py
python manage.py migrate
python manage.py seed_editorial_content
python manage.py test customer staff
```

