# kiemtra01 - 4-Service Django Commerce

## 1. Overview

This repo now runs a 4-service architecture:

- `user_service`: shared auth source, customer/staff web UI, gateway/orchestrator, editorial content, chatbot proxy.
- `product_service`: unified catalog API with 10 categories and 100 seeded products.
- `order_service`: cart/saved/compare/order/shipping ownership plus analytics and legacy order import.
- `chatbot_service`: hybrid chatbot retrieval with file RAG, optional `model_best` category prediction, optional Neo4j graph context, and PostgreSQL-backed behavior events.

Databases:

- MySQL: `user_service`, `order_service`
- PostgreSQL: `product_service`, `chatbot_service`
- Neo4j: optional behavior knowledge graph for `chatbot_service` Phase 4/5 retrieval

Public entry points:

- Customer + staff UI: `http://localhost:8000/` and `http://localhost:8003/`
- Dedicated gateway workspace: `http://localhost:8000/gateway/`
- Product API: `http://localhost:8001/api/`
- Chatbot API: `http://localhost:8005/api/`
- Neo4j Browser: `http://localhost:7474/`

## 2. Service Matrix

| Service | Role | DB | Host Port |
|---|---|---|---:|
| `user_service` | Customer/staff UI, auth, gateway, editorial content | MySQL `user_db` | `8000`, `8003` |
| `product_service` | Unified catalog API | PostgreSQL `product_db` | `8001` |
| `order_service` | Cart/order/shipping API, internal-only by default, consumed by `user_service` | MySQL `order_db` | internal |
| `chatbot_service` | Chatbot + RAG + behavior persistence | PostgreSQL `chatbot_db` | `8005` |
| `neo4j` | Behavior graph KB for chatbot context queries | Neo4j graph store | `7474`, `7687` |

## 3. Key Contracts

Customer-facing routes kept stable:

- `/customer/login/`
- `/customer/register/`
- `/customer/dashboard/`
- `/customer/products/<category_slug>/<id>/`
- `/customer/cart/`
- `/customer/orders/`
- `/customer/chatbot/reply/`

Staff-facing routes:

- `/staff/login/`
- `/staff/register/`
- `/staff/dashboard/`
- `/staff/items/`
- `/staff/customers/`
- `/staff/orders/`

Catalog API:

- `GET /api/categories/`
- `GET /api/products/`
- `GET /api/products/<id>/`
- `POST/PUT/DELETE /api/products/...` with `X-Staff-Key`

Order API is internal-first and used by `user_service` for cart/saved/compare/checkout/orders/shipping. The host port is exposed for smoke tests and operational inspection.

Dedicated gateway code now lives in:

- `services/user_service/customer/api_gateway/definitions.py`
- `services/user_service/customer/api_gateway/registry.py`

The HTML inspection page is available at `/gateway/` and the JSON index is available at `/gateway/apis/`.

## 4. Environment

Copy env template:

```powershell
copy .env.example .env
```

Important variables:

- `USER_MYSQL_DATABASE`, `USER_MYSQL_USER`, `USER_MYSQL_PASSWORD`
- `ORDER_MYSQL_DATABASE`, `ORDER_MYSQL_USER`, `ORDER_MYSQL_PASSWORD`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `PRODUCT_POSTGRES_DB`, `CHATBOT_POSTGRES_DB`
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `USER_SERVICE_URL`
- `PRODUCT_SERVICE_URL`
- `ORDER_SERVICE_URL`
- `CHATBOT_SERVICE_URL`
- `ORDER_SERVICE_INTERNAL_KEY`
- `STAFF_API_KEY`
- `CHATBOT_INGEST_KEY`
- `LLM_PROVIDER`, `GEMMA_MODEL`, `GEMINI_API_KEY`, `CHATBOT_GEMINI_MODEL`
- Phase 5 runtime artifacts in `services/chatbot_service/chatbot/artifacts/`: `model_best.keras`, `label_encoder.json`, `tokenizer_or_vocab.json`

## 5. Runbook

Start everything:

```bash
docker compose up --build -d
```

Check containers:

```bash
docker compose ps
docker compose logs --tail=120 user_service order_service product_service chatbot_service
```

Stop:

```bash
docker compose down
```

## 6. Migrations And Seed

Run migrations:

```bash
docker compose exec user_service python manage.py migrate
docker compose exec order_service python manage.py migrate
docker compose exec product_service python manage.py migrate
docker compose exec chatbot_service python manage.py migrate
```

Seed catalog + editorial content:

```bash
docker compose exec product_service python manage.py seed_products --reset
docker compose exec user_service python manage.py seed_editorial_content --reset
```

Build chatbot artifacts:

```bash
docker compose exec chatbot_service python manage.py build_chat_kb --max-products 160
docker compose exec chatbot_service python manage.py train_behavior_model
docker compose exec chatbot_service python manage.py import_behavior_graph --reset
```

Neo4j graph notes:

- Browser: `http://localhost:7474/`
- Default login from `.env.example`: user `neo4j`, password `graph_password`
- Demo graph image is written to `services/chatbot_service/chatbot/artifacts/behavior_graph_demo.svg`
- Cypher samples and schema notes live in `docs/neo4j_behavior_graph.md`
- `chatbot_service` still starts and `/api/chat/reply/` still works when Neo4j is unavailable; Phase 5 falls back to file-based RAG automatically.

## 7. Legacy Migration

Merge legacy customer/staff accounts into `user_service`:

```bash
docker compose exec user_service python manage.py migrate_legacy_users --dry-run
docker compose exec user_service python manage.py migrate_legacy_users
```

Import legacy order history from `customer_db` into `order_service`:

```bash
docker compose exec order_service python manage.py import_legacy_orders
```

Backfill chatbot behavior from current `order_service` history:

```bash
docker compose exec user_service python manage.py backfill_chatbot_behavior --dry-run
docker compose exec user_service python manage.py backfill_chatbot_behavior
```

## 8. Verification Checklist

- `docker compose up --build -d` reaches a clean state with:
  - MySQL healthy before `user_service` and `order_service` bootstrap/migrate
  - PostgreSQL healthy before `product_service` and `chatbot_service` bootstrap/migrate
- Customer register/login works.
- Customer dashboard loads unified categories/products.
- Saved/compare/cart/checkout/orders/payment work through `order_service`.
- Staff login works.
- Staff can create/update/delete products across multiple categories.
- Staff can view customers and update shipping at `/staff/orders/`.
- `build_chat_kb` and `train_behavior_model` complete successfully.
- If `model_best.keras` artifacts are present and the Keras backend is available, `/api/chat/reply/` uses them to predict the top category before retrieval.
- `import_behavior_graph --reset` completes successfully and sample Cypher queries return rows in Neo4j Browser.
- If Neo4j is unavailable, `chatbot_service` still starts and `/api/chat/reply/` falls back to file-based RAG and rule-based generation when needed.
- `/customer/chatbot/reply/` returns recommendations with valid `category_slug`.
- `docker compose ps` shows:
  - `user_service` on `8000` and `8003`
  - `product_service` on `8001`
  - `order_service` reachable on the Docker network only via `http://order-service:8000`
  - `chatbot_service` on `8005`
  - `neo4j` on `7474` and `7687`
- No runtime env or Docker hostname references remain for `customer_service`, `staff_service`, `laptop_service`, `mobile_service`, or `accessory_service`.

## 9. Smoke Commands

PowerShell examples:

```powershell
Invoke-WebRequest http://localhost:8000/customer/login/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8001/api/categories/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8005/api/chat/reply/ -Method Post -ContentType 'application/json' -Body '{"message":"goi y laptop hoc tap"}' | Select-Object -ExpandProperty StatusCode
docker compose exec user_service python manage.py shell -c "import requests; print(requests.get('http://order-service:8000/api/staff/orders/', headers={'X-Internal-Key':'dev-order-internal-key'}).status_code)"
```

Only remove the legacy service folders after these smoke checks pass for the 4 target services.

## 10. Chatbot Artifacts

Host bind-mounted artifacts live under:

- `services/chatbot_service/chatbot/artifacts/knowledge_base.json`
- `services/chatbot_service/chatbot/artifacts/model_behavior.json`
- `services/chatbot_service/chatbot/artifacts/model_best.keras`
- `services/chatbot_service/chatbot/artifacts/label_encoder.json`
- `services/chatbot_service/chatbot/artifacts/tokenizer_or_vocab.json`
- `services/chatbot_service/chatbot/artifacts/training_data_behavior.json`
- `services/chatbot_service/chatbot/artifacts/runtime_config.json`
- `services/chatbot_service/chatbot/artifacts/behavior_graph_demo.svg`

## 11. Notes

- No service uses SQLite.
- MySQL/PostgreSQL bootstrap scripts are expected to reconcile reused Docker volumes to `user_db`, `order_db`, `product_db`, and `chatbot_db` without requiring manual volume deletion.
- Legacy cart/saved/compare data is intentionally not migrated.
- Legacy orders are preserved as snapshot history and are not forced to relink to the new catalog taxonomy.
- `user_service` remains the recovery owner for chatbot behavior via `backfill_chatbot_behavior`.

## 12. Phase 6 Demo Flow

Phase 6 keeps the customer routes stable and extends the existing e-commerce UI with AI in 3 places:

- `/customer/dashboard/` now renders an `AI goi y cho ban` block above the search results, driven by the Phase 5 chatbot backend and scoped to the current filters/search intent.
- `/customer/cart/` now renders a `Co the mua kem` block under the active cart, driven by the same chatbot backend and filtered away from products already in the basket.
- The floating chat widget stays in the existing project style and still posts to `/customer/chatbot/reply/`; only the backend intelligence source is the Phase 5 hybrid chatbot service.

Recommended live demo order:

1. Start the full stack with `docker compose up --build -d`.
2. Open `http://localhost:8000/customer/register/` and create a customer account, or sign in with an existing seeded/demo account.
3. Browse `http://localhost:8000/customer/dashboard/`, search by keyword/category, and capture the `AI goi y cho ban` block together with the matching product results.
4. Add 1-2 items to cart, open `http://localhost:8000/customer/cart/`, and capture the `Co the mua kem` block.
5. Open the existing chat widget, ask for a product suggestion, and capture the widget reply with recommendation cards/citations.
6. Optionally open Neo4j Browser at `http://localhost:7474/` to show the behavior graph context behind the chatbot retrieval layer.

## 13. Submission Evidence

Use `docs/phase-6-submission-kit.md` as the checklist for the PDF pack. The required evidence already maps to repo artifacts and UI screens:

- 20-row data sample: `services/chatbot_service/chatbot/artifacts/data_user500_sample20.csv`
- Metric comparison table: `services/chatbot_service/chatbot/artifacts/metrics_comparison.csv`
- Confusion matrix images: `services/chatbot_service/chatbot/artifacts/confusion_matrix_*.png`
- Training history plots: `services/chatbot_service/chatbot/artifacts/history_*.png`
- Neo4j graph image: `services/chatbot_service/chatbot/artifacts/behavior_graph_demo.svg`
- Chat widget screenshot: save to `docs/evidence/screenshots/chat-widget.png`
- Dashboard AI screenshot: save to `docs/evidence/screenshots/dashboard-ai.png`
- Cart AI screenshot: save to `docs/evidence/screenshots/cart-ai.png`
