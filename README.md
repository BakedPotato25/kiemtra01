# Final Essay - Django Commerce Microservices and AI

## 1. Overview

This repository is the final essay implementation package for the Software Architecture and Design course. The essay topic is building an e-commerce system using microservices and AI, with Docker Compose, Django services, an Nginx gateway, database-per-service storage, and an AI chatbot/recommendation service.

The implementation follows the final essay structure in `EssayV1/tieuluan_Monhoc_KientrucThietke_PM_04-2026.pdf`: monolithic architecture, microservices, Domain Driven Design, e-commerce service decomposition, AI service design, and complete-system deployment.

This repo runs a 6-service architecture:

- `user_service`: shared auth source, customer/staff web UI, gateway/orchestrator, editorial content, chatbot proxy.
- `product_service`: unified catalog API with 10 categories and 100 seeded products.
- `order_service`: cart/saved/compare/order item ownership, checkout orchestration, payment/shipping snapshots, analytics, and legacy order import.
- `payment_service`: internal payment records for order checkout and pay-order confirmation.
- `shipping_service`: internal shipment records and staff-managed shipping status transitions.
- `chatbot_service`: hybrid chatbot retrieval with file RAG, optional `model_best` category prediction, optional Neo4j graph context, and PostgreSQL-backed behavior events.

Databases:

- MySQL: `user_service`, `order_service`
- PostgreSQL: `product_service`, `chatbot_service`, `payment_service`, `shipping_service`
- Neo4j: optional behavior knowledge graph for `chatbot_service` behavior-context retrieval

Public entry points:

- Nginx API Gateway, primary entrypoint: `http://localhost:8080/`
- Customer + staff UI direct debug ports: `http://localhost:8000/` and `http://localhost:8003/`
- Dedicated gateway workspace: `http://localhost:8080/gateway/`
- Product API direct debug port: `http://localhost:8001/api/`
- Chatbot API direct debug port: `http://localhost:8005/api/`
- Neo4j Browser: `http://localhost:7474/`

API gateway decision:

- There is no standalone Django service named `api_gateway`.
- The public reverse proxy is the Docker Compose service `gateway`, backed by `docker/gateway/nginx.conf`.
- Application-level gateway metadata and orchestration live in `user_service`, under `services/user_service/customer/api_gateway/`.
- A new `api_gateway` service is not needed for the current architecture because Nginx handles public path routing and `user_service` owns browser auth/session orchestration.

Final essay package:

- Main report source: `EssayV1/essay_from_toc.tex`
- Reference report structure: `EssayV1/tieuluan_Monhoc_KientrucThietke_PM_04-2026.pdf`
- Final diagram upload folder for Overleaf: `EssayV1/final_diagram_images/`
- Image upload checklist: `EssayV1/images_to_upload.md`
- Demo runbook: `DEMO_RUNBOOK.md`
- Gateway URL index: `docker/gateway/README.md`

## 2. Service Matrix

Current final runtime architecture:

| Service | Role | DB | Host Port |
|---|---|---|---:|
| `gateway` | Nginx primary public entrypoint for UI and API paths | none | `8080` |
| `user_service` | Customer/staff UI, Django session auth, JWT API auth, gateway metadata, editorial content | MySQL `user_db` | `8000`, `8003` debug |
| `product_service` | Unified catalog API | PostgreSQL `product_db` | `8001` |
| `order_service` | Cart/order API and payment/shipping orchestration, internal-only by default, consumed by `user_service` | MySQL `order_db` | internal |
| `payment_service` | Payment records and confirmation lifecycle | PostgreSQL `payment_db` | internal |
| `shipping_service` | Shipment records and shipping status lifecycle | PostgreSQL `shipping_db` | internal |
| `chatbot_service` | Chatbot + RAG + behavior persistence | PostgreSQL `chatbot_db` | `8005` |
| `neo4j` | Behavior graph KB for chatbot context queries | Neo4j graph store | `7474`, `7687` |

Service README index:

- `services/user_service/README.md`
- `services/product_service/README.md`
- `services/order_service/README.md`
- `services/payment_service/README.md`
- `services/shipping_service/README.md`
- `services/chatbot_service/README.md`
- `docker/gateway/README.md`

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

Auth modes coexist:

- Browser UI uses Django session auth for `/customer/*`, `/staff/*`, and `/admin/`.
- Customer and staff UI sessions use separate cookies (`customer_sessionid`, `staff_sessionid`) so both roles can be demoed in one browser without logging each other out.
- API auth uses JWT through `/api/auth/register/`, `/api/auth/token/`, `/api/auth/token/refresh/`, and `/api/auth/me/`.
- Both auth surfaces are exposed through the Nginx gateway on `http://localhost:8080/`; direct `user_service` ports are for local debugging.

Catalog API:

- `GET /api/categories/`
- `GET /api/products/`
- `GET /api/products/<id>/`
- `POST/PUT/DELETE /api/products/...` with `X-Staff-Key`

Order API is internal-first and used by `user_service` for cart/saved/compare/checkout/orders/shipping. Checkout creates the local pending order, then creates pending records in `payment_service` and `shipping_service`. Pay-order confirms through `payment_service`; staff shipping updates go through `shipping_service` and then sync the current `order_service.shipping_status` snapshot for the existing UI.

Dedicated gateway code now lives in:

- `services/user_service/customer/api_gateway/definitions.py`
- `services/user_service/customer/api_gateway/registry.py`

The HTML inspection page is available at `/gateway/` and the JSON index is available at `/gateway/apis/`.

Nginx gateway routing lives in `docker/gateway/nginx.conf` and is exposed on `http://localhost:8080/` as the primary public entrypoint without removing the direct debug ports above. It routes `/`, `/customer/`, `/staff/`, `/admin/`, `/gateway/`, and `/api/auth/` to `user-service`; `/api/products/` and `/api/categories/` to `product-service`; `/api/cart/`, `/api/saved/`, `/api/compare/`, `/api/checkout/`, `/api/orders/`, `/api/staff/orders/`, `/api/analytics/`, and `/api/internal/` to `order-service`; `/api/payments/` to `payment-service`; `/api/shipments/` to `shipping-service`; `/api/chat/` to `chatbot-service`.

## 4. Environment

Copy env template:

```powershell
copy .env.example .env
```

Important variables:

- `USER_MYSQL_DATABASE`, `USER_MYSQL_USER`, `USER_MYSQL_PASSWORD`
- `ORDER_MYSQL_DATABASE`, `ORDER_MYSQL_USER`, `ORDER_MYSQL_PASSWORD`
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `PRODUCT_POSTGRES_DB`, `CHATBOT_POSTGRES_DB`, `PAYMENT_POSTGRES_DB`, `SHIPPING_POSTGRES_DB`
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
- `USER_SERVICE_URL`
- `PRODUCT_SERVICE_URL`
- `ORDER_SERVICE_URL`
- `PAYMENT_SERVICE_URL`
- `SHIPPING_SERVICE_URL`
- `CHATBOT_SERVICE_URL`
- `ORDER_SERVICE_INTERNAL_KEY`
- `PAYMENT_SERVICE_INTERNAL_KEY`
- `SHIPPING_SERVICE_INTERNAL_KEY`
- `STAFF_API_KEY`
- `CHATBOT_INGEST_KEY`
- `LLM_PROVIDER`, `GEMMA_MODEL`, `GEMINI_API_KEY`, `CHATBOT_GEMINI_MODEL`
- AI runtime artifacts in `services/chatbot_service/chatbot/artifacts/`: `model_best.keras`, `label_encoder.json`, `tokenizer_or_vocab.json`

## 5. Runbook

If Docker Desktop or the Docker service is not running, start Docker first, then run the same commands below. On Windows PowerShell, useful recovery commands are:

```powershell
Start-Service -Name com.docker.service
docker compose config --quiet
docker compose up --build -d
docker compose ps -a
docker compose logs --tail=120 gateway user_service order_service payment_service shipping_service product_service chatbot_service
```

Start everything:

```bash
docker compose up --build -d
```

Check containers:

```bash
docker compose ps
docker compose logs --tail=120 user_service order_service payment_service shipping_service product_service chatbot_service
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
docker compose exec payment_service python manage.py migrate
docker compose exec shipping_service python manage.py migrate
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
- `chatbot_service` still starts and `/api/chat/reply/` still works when Neo4j is unavailable; chatbot retrieval falls back to file-based RAG automatically.

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
  - PostgreSQL healthy before `product_service`, `payment_service`, `shipping_service`, and `chatbot_service` bootstrap/migrate
- Customer register/login works.
- Customer dashboard loads unified categories/products.
- Saved/compare/cart/checkout/orders/payment work through `order_service`, with payment records delegated to `payment_service`.
- Staff login works.
- Staff can create/update/delete products across multiple categories.
- Staff can view customers and update shipping at `/staff/orders/`, with shipment records delegated to `shipping_service` and order snapshots kept current.
- `build_chat_kb` and `train_behavior_model` complete successfully.
- If `model_best.keras` artifacts are present and the Keras backend is available, `/api/chat/reply/` uses them to predict the top category before retrieval.
- `import_behavior_graph --reset` completes successfully and sample Cypher queries return rows in Neo4j Browser.
- If Neo4j is unavailable, `chatbot_service` still starts and `/api/chat/reply/` falls back to file-based RAG and rule-based generation when needed.
- `/customer/chatbot/reply/` returns recommendations with valid `category_slug`.
- `docker compose ps` shows:
  - `gateway` on `8080`
  - `user_service` on `8000` and `8003`
  - `product_service` on `8001`
  - `order_service` reachable on the Docker network only via `http://order-service:8000`
  - `payment_service` reachable on the Docker network only via `http://payment-service:8000`
  - `shipping_service` reachable on the Docker network only via `http://shipping-service:8000`
  - `chatbot_service` on `8005`
  - `neo4j` on `7474` and `7687`
- No runtime env or Docker hostname references remain for `customer_service`, `staff_service`, `laptop_service`, `mobile_service`, or `accessory_service`.

## 9. Latest Verification

Last full verification: June 11, 2026.

Verified commands:

- `docker compose config --quiet`
- `docker compose up --build -d`
- `docker compose ps -a`
- `docker compose logs --tail=120` for gateway and all six Django services
- `docker compose exec -T product_service python manage.py seed_products`
- `docker compose exec -T user_service python manage.py seed_editorial_content`
- `docker compose exec -T chatbot_service python manage.py build_chat_kb --max-products 160`
- `docker compose exec -T chatbot_service python manage.py train_behavior_model`
- `docker compose exec -T chatbot_service python manage.py import_behavior_graph --reset`

Service tests passed:

- `user_service`: `python manage.py test customer staff` - 28 tests
- `product_service`: `python manage.py test catalog` - 6 tests
- `order_service`: `python manage.py test orders` - 11 tests
- `payment_service`: `python manage.py test payments` - 5 tests
- `shipping_service`: `python manage.py test shipments` - 6 tests
- `chatbot_service`: `python manage.py test chatbot` - 15 tests

Gateway smoke passed through `http://localhost:8080` with smoke `user_id=62`, `order_id=145`, and `product_id=1`. The smoke covered gateway registry, catalog, JWT auth, saved items, compare, cart, checkout, payment record lookup, shipment record lookup, pay order, shipping transitions through `preparing`, `shipped`, and `delivered`, order list, analytics, behavior source export, direct chatbot reply, customer analytics proxy, customer session login/pages, customer chatbot proxy, staff registration/login/pages, and staff orders.

## 10. Smoke Commands

PowerShell examples through the primary Nginx gateway on port `8080`:

```powershell
Invoke-WebRequest http://localhost:8080/customer/login/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8080/staff/login/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8080/gateway/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8080/api/categories/ | Select-Object -ExpandProperty StatusCode
$smokeUser = "smoke_" + (Get-Date -Format "yyyyMMddHHmmss")
$authBody = @{username=$smokeUser; email="$smokeUser@example.test"; password="SmokePass123!"; confirm_password="SmokePass123!"} | ConvertTo-Json
Invoke-WebRequest http://localhost:8080/api/auth/register/ -Method Post -ContentType 'application/json' -Body $authBody | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8080/api/chat/reply/ -Method Post -ContentType 'application/json' -Body '{"message":"goi y laptop hoc tap"}' | Select-Object -ExpandProperty StatusCode
docker compose exec user_service python manage.py shell -c "import requests; print(requests.get('http://order-service:8000/api/staff/orders/', headers={'X-Internal-Key':'dev-order-internal-key'}).status_code)"
```

Use direct service ports (`8000`, `8001`, `8005`) only when debugging a specific container after the gateway smoke checks identify a problem.

Only remove the legacy service folders after these smoke checks pass for the current target services.

## 11. Chatbot Artifacts

Host bind-mounted artifacts live under:

- `services/chatbot_service/chatbot/artifacts/knowledge_base.json`
- `services/chatbot_service/chatbot/artifacts/model_behavior.json`
- `services/chatbot_service/chatbot/artifacts/model_best.keras`
- `services/chatbot_service/chatbot/artifacts/label_encoder.json`
- `services/chatbot_service/chatbot/artifacts/tokenizer_or_vocab.json`
- `services/chatbot_service/chatbot/artifacts/training_data_behavior.json`
- `services/chatbot_service/chatbot/artifacts/runtime_config.json`
- `services/chatbot_service/chatbot/artifacts/behavior_graph_demo.svg`

## 12. Notes

- No service uses SQLite.
- MySQL/PostgreSQL bootstrap scripts are expected to reconcile reused Docker volumes to `user_db`, `order_db`, `product_db`, `payment_db`, `shipping_db`, and `chatbot_db` without requiring manual volume deletion.
- Legacy cart/saved/compare data is intentionally not migrated.
- Legacy orders are preserved as snapshot history and are not forced to relink to the new catalog taxonomy.
- `user_service` remains the recovery owner for chatbot behavior via `backfill_chatbot_behavior`.

## 13. Final Demo Flow

The final demo keeps the customer routes stable and shows the e-commerce UI with AI in 3 places:

- `/customer/dashboard/` renders an AI recommendation block above the search results, driven by the hybrid chatbot backend and scoped to the current filters/search intent.
- `/customer/cart/` renders a buy-together recommendation block under the active cart, driven by the same chatbot backend and filtered away from products already in the basket.
- The floating chat widget stays in the existing project style and still posts to `/customer/chatbot/reply/`; the backend intelligence source is the hybrid chatbot service.

Recommended live demo order:

1. Start the full stack with `docker compose up --build -d`.
2. Open `http://localhost:8080/customer/register/` and create a customer account, or sign in with an existing seeded/demo account.
3. Browse `http://localhost:8080/customer/dashboard/`, search by keyword/category, and capture the AI recommendation block together with the matching product results.
4. Add 1-2 items to cart, open `http://localhost:8080/customer/cart/`, and capture the buy-together recommendation block.
5. Open the existing chat widget, ask for a product suggestion, and capture the widget reply with recommendation cards/citations.
6. Optionally open Neo4j Browser at `http://localhost:7474/` to show the behavior graph context behind the chatbot retrieval layer.

## 14. Final Essay Evidence

Use the files under `EssayV1/` as the final report package. The main report is `EssayV1/essay_from_toc.tex`, and the Overleaf image checklist is `EssayV1/images_to_upload.md`. The required implementation evidence maps to repo artifacts and UI screens:

- Final LaTeX report: `EssayV1/essay_from_toc.tex`
- Reference report structure: `EssayV1/tieuluan_Monhoc_KientrucThietke_PM_04-2026.pdf`
- Final report diagrams: `EssayV1/final_diagram_images/`
- Visual Paradigm source diagrams: `EssayV1/Visual Paradigm Diagrams/`
- Generated architecture diagrams: `EssayV1/generated_diagrams/`
- 20-row data sample: `services/chatbot_service/chatbot/artifacts/data_user500_sample20.csv`
- Metric comparison table: `services/chatbot_service/chatbot/artifacts/metrics_comparison.csv`
- Confusion matrix images: `services/chatbot_service/chatbot/artifacts/confusion_matrix_*.png`
- Training history plots: `services/chatbot_service/chatbot/artifacts/history_*.png`
- AI runtime artifacts: `services/chatbot_service/chatbot/artifacts/knowledge_base.json`, `model_best.keras`, `label_encoder.json`, `tokenizer_or_vocab.json`, `runtime_config.json`
- Neo4j graph image: `services/chatbot_service/chatbot/artifacts/behavior_graph_demo.svg`
- Neo4j notes and Cypher: `docs/neo4j_behavior_graph.md`, `docs/neo4j_behavior_graph_queries.cypher`
- Chat widget screenshot: save to `docs/evidence/screenshots/chat-widget.png`
- Dashboard AI screenshot: save to `docs/evidence/screenshots/dashboard-ai.png`
- Cart AI screenshot: save to `docs/evidence/screenshots/cart-ai.png`
- Neo4j Browser screenshots: save to `docs/evidence/screenshots/neo4j-browser.png` and `docs/evidence/screenshots/neo4j-browser-2.png`
