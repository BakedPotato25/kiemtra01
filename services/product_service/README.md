# product_service

`product_service` is the unified Django REST catalog API. It owns the 10-category taxonomy and the 100 seeded demo products used by the storefront, staff item management, and chatbot knowledge base.

## Runtime

- Compose service: `product_service`
- Docker hostname: `product-service`
- Debug port: `8001`
- Public gateway paths: `/api/categories/`, `/api/products/`
- Database: PostgreSQL `product_db`

## Key Routes

- `GET /api/categories/`
- `GET /api/products/`
- `GET /api/products/<id>/`
- `POST /api/products/` with `X-Staff-Key`
- `PUT /api/products/<id>/` with `X-Staff-Key`
- `DELETE /api/products/<id>/` with `X-Staff-Key`

## Data

Seed data lives in `catalog/seed_data.py`. The seed command is idempotent and keeps the runtime catalog aligned with the fixture taxonomy.

## Commands

```bash
python bootstrap_postgres.py
python manage.py migrate
python manage.py seed_products
python manage.py test catalog
```

