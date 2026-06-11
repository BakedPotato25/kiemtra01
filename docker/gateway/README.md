# gateway

`gateway` is the Nginx public entrypoint for the Docker Compose stack. It exposes `http://localhost:8080/` and routes browser and API traffic to Docker service hostnames.

## Runtime

- Compose service: `gateway`
- Docker hostname: `gateway`
- Public port: `8080`
- Config file: `docker/gateway/nginx.conf`
- Image: `nginx:1.27-alpine`

## Routing

- `user-service`: `/`, `/customer/`, `/staff/`, `/admin/`, `/gateway/`, `/api/auth/`
- `product-service`: `/api/products/`, `/api/categories/`
- `order-service`: `/api/cart/`, `/api/saved/`, `/api/compare/`, `/api/checkout/`, `/api/orders/`, `/api/staff/orders/`, `/api/analytics/`, `/api/internal/`
- `payment-service`: `/api/payments/`
- `shipping-service`: `/api/shipments/`
- `chatbot-service`: `/api/chat/`

## URL Index

Use `http://localhost:8080` as the main public base URL.

### UI And Gateway Pages

| Name | URL |
|---|---|
| Home/customer landing | `http://localhost:8080/` |
| Gateway dashboard | `http://localhost:8080/gateway/` |
| Gateway API registry | `http://localhost:8080/gateway/apis/` |
| Django admin | `http://localhost:8080/admin/` |
| Customer login | `http://localhost:8080/customer/login/` |
| Customer register | `http://localhost:8080/customer/register/` |
| Customer logout | `http://localhost:8080/customer/logout/` |
| Customer dashboard | `http://localhost:8080/customer/dashboard/` |
| Product detail | `http://localhost:8080/customer/products/<category_slug>/<product_id>/` |
| Blog detail | `http://localhost:8080/customer/blog/<slug>/` |
| Saved list | `http://localhost:8080/customer/saved/` |
| Toggle saved item | `http://localhost:8080/customer/saved/toggle/` |
| Compare list | `http://localhost:8080/customer/compare/` |
| Toggle compare item | `http://localhost:8080/customer/compare/toggle/` |
| Remove compare item | `http://localhost:8080/customer/compare/remove/<item_id>/` |
| Cart page | `http://localhost:8080/customer/cart/` |
| Add to cart | `http://localhost:8080/customer/cart/add/` |
| Remove cart item | `http://localhost:8080/customer/cart/remove/<item_id>/` |
| Customer chatbot proxy | `http://localhost:8080/customer/chatbot/reply/` |
| Checkout page | `http://localhost:8080/customer/checkout/` |
| Customer orders | `http://localhost:8080/customer/orders/` |
| Pay order | `http://localhost:8080/customer/orders/<order_id>/pay/` |
| Staff analytics proxy | `http://localhost:8080/customer/staff/analytics/` |
| Staff login | `http://localhost:8080/staff/login/` |
| Staff register | `http://localhost:8080/staff/register/` |
| Staff logout | `http://localhost:8080/staff/logout/` |
| Staff dashboard | `http://localhost:8080/staff/dashboard/` |
| Staff items/products | `http://localhost:8080/staff/items/` |
| Staff customers | `http://localhost:8080/staff/customers/` |
| Staff customer detail | `http://localhost:8080/staff/customers/<user_id>/` |
| Staff edit customer | `http://localhost:8080/staff/customers/<user_id>/edit/` |
| Staff toggle customer active | `http://localhost:8080/staff/customers/<user_id>/toggle-active/` |
| Staff reset customer password | `http://localhost:8080/staff/customers/<user_id>/reset-password/` |
| Staff orders | `http://localhost:8080/staff/orders/` |

### Public APIs

| Service | URLs |
|---|---|
| Auth | `/api/auth/register/`, `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/me/` |
| Catalog | `/api/categories/`, `/api/categories/<id>/`, `/api/products/`, `/api/products/<id>/` |
| Cart | `/api/cart/`, `/api/cart/<item_id>/` |
| Saved | `/api/saved/`, `/api/saved/toggle/` |
| Compare | `/api/compare/`, `/api/compare/toggle/`, `/api/compare/<item_id>/` |
| Checkout/orders | `/api/checkout/`, `/api/orders/`, `/api/orders/<order_id>/pay/` |
| Staff order API | `/api/staff/orders/`, `/api/staff/orders/<order_id>/shipping/` |
| Analytics/internal | `/api/analytics/customers/`, `/api/internal/behavior-source/` |
| Payments | `/api/payments/`, `/api/payments/<payment_id>/`, `/api/payments/by-order/<order_id>/`, `/api/payments/<payment_id>/confirm/`, `/api/payments/<payment_id>/cancel/` |
| Shipments | `/api/shipments/`, `/api/shipments/<shipment_id>/`, `/api/shipments/by-order/<order_id>/`, `/api/shipments/<shipment_id>/status/` |
| Chatbot | `/api/chat/reply/`, `/api/chat/ingest-behavior/` |

### Direct Debug URLs

These ports are for development/debugging only. Prefer the gateway URL during demo.

| Service | URL |
|---|---|
| `user_service` root | `http://localhost:8000/` |
| `user_service` customer login | `http://localhost:8000/customer/login/` |
| `user_service` staff debug | `http://localhost:8003/staff/login/` |
| `product_service` categories | `http://localhost:8001/api/categories/` |
| `product_service` products | `http://localhost:8001/api/products/` |
| `chatbot_service` reply | `http://localhost:8005/api/chat/reply/` |
| Neo4j Browser | `http://localhost:7474/` |
| Neo4j Bolt | `bolt://localhost:7687` |

## API Gateway Decision

This project does not need a separate `api_gateway` application service right now. Nginx handles path routing, while `user_service/customer/api_gateway/` contains the application-level gateway registry and inspection metadata for `/gateway/` and `/gateway/apis/`.

## Commands

```bash
docker compose config --quiet
docker compose restart gateway
docker compose exec -T gateway nginx -t
docker compose logs --tail=120 gateway
```
