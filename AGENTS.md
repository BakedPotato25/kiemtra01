# AGENTS.md

## Project overview
This repo is a Docker-based Django commerce demo with 6 application services, an Nginx gateway, and database services.

- `gateway`: Nginx public entrypoint on `8080`, routing browser and API traffic to service hostnames.
- `user_service`: shared auth source, customer/staff web UI, session UI, JWT API auth, gateway/orchestrator, editorial content, chatbot proxy, and legacy user migration.
- `product_service`: unified catalog API with 10 categories and 100 seeded demo products.
- `order_service`: cart/saved/compare/order ownership, checkout orchestration, order analytics, and legacy order import.
- `payment_service`: internal payment record and confirmation lifecycle.
- `shipping_service`: internal shipment record and shipping status lifecycle.
- `chatbot_service`: chat reply, behavior ingest, category-affinity artifacts, RAG knowledge base, and PostgreSQL-backed behavior persistence.
- `neo4j`: optional graph KB backing Phase 4/5 behavior-context queries for `chatbot_service`.

## Goals
- Keep changes small and reviewable.
- Prefer fixing root causes over patching symptoms.
- Do not break customer, staff, product, order, payment, shipping, or chatbot flows during cutover.

## Coding rules
- Preserve the 6-service boundaries: auth/UI in `user_service`, catalog in `product_service`, commerce state in `order_service`, payments in `payment_service`, shipping in `shipping_service`, AI in `chatbot_service`.
- Reuse local helpers, service clients, and management commands before adding new ones.
- Keep response shapes and public routes stable unless the task explicitly changes them.
- Keep service URLs aligned with the Docker hostnames `user-service`, `product-service`, `order-service`, `payment-service`, `shipping-service`, and `chatbot-service`.
- Keep Nginx gateway on `8080` as the primary public entrypoint. Direct service ports are development/debug surfaces only.
- Keep JWT API auth (`/api/auth/*`) and Django session UI auth (`/customer/*`, `/staff/*`) coexisting in `user_service`.
- Keep the cutover port map aligned with Docker Compose: gateway on `8080`, `user_service` on `8000` and `8003`, `product_service` on `8001`, `order_service` internal-only, `payment_service` internal-only, `shipping_service` internal-only, and `chatbot_service` on `8005`.
- Keep chatbot artifacts file-based under `services/chatbot_service/chatbot/artifacts`.
- Keep Neo4j wiring env-driven (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`) and isolated so customer, product, order, payment, shipping, and chatbot startup still work without changing their public contracts.
- Use `user_service`'s `backfill_chatbot_behavior` command as the primary recovery path for `BehaviorEvent`.
- When changing models, add migrations and update `.env.example`, `docker-compose.yml`, `README.md`, and the relevant `AGENTS.md` files in the same change.

## Testing
- Run relevant tests in each touched service with `python manage.py test`.
- Add tests for new behavior when the touched service has a natural place for them.
- Do not change unrelated failing tests.
- When startup wiring changes, verify MySQL healthcheck + `bootstrap_mysql.py` for `user_service` and `order_service`, and PostgreSQL bootstrap for `product_service`, `payment_service`, `shipping_service`, and `chatbot_service`.
- Do not delete legacy service folders until `docker compose up --build -d` and gateway smoke checks succeed for all target services.
- When chatbot/category logic changes, verify `build_chat_kb`, `train_behavior_model`, and the proxied `/customer/chatbot/reply/` flow together.

## Dependencies
- Do not add new packages unless necessary.
- Keep dependencies service-local in `services/<service>/requirements.txt`.
- Update docs and env wiring whenever runtime configuration changes.

## Output expectations
- Explain what changed.
- List touched files.
- Mention tradeoffs or remaining risks.
- Note what you verified, including tests run and any manual checks.
