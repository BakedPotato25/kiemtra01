# AGENTS.md

## Project overview
This repo is a Docker-based Django commerce demo with 4 application services and 2 database services.

- `user_service`: shared auth source, customer/staff web UI, gateway/orchestrator, editorial content, chatbot proxy, and legacy user migration.
- `product_service`: unified catalog API with 10 categories and 100 seeded demo products.
- `order_service`: cart/saved/compare/order/shipping ownership, checkout/payment flow, order analytics, and legacy order import.
- `chatbot_service`: chat reply, behavior ingest, category-affinity artifacts, RAG knowledge base, and PostgreSQL-backed behavior persistence.

## Goals
- Keep changes small and reviewable.
- Prefer fixing root causes over patching symptoms.
- Do not break customer, staff, product, order, or chatbot flows during cutover.

## Coding rules
- Preserve the new 4-service boundaries: auth/UI in `user_service`, catalog in `product_service`, commerce state in `order_service`, AI in `chatbot_service`.
- Reuse local helpers, service clients, and management commands before adding new ones.
- Keep response shapes and public routes stable unless the task explicitly changes them.
- Keep service URLs aligned with the Docker hostnames `user-service`, `product-service`, `order-service`, and `chatbot-service`.
- Keep the cutover port map aligned with Docker Compose: `user_service` on `8000` and `8003`, `product_service` on `8001`, `order_service` internal-only on the Docker network, and `chatbot_service` on `8005`.
- Keep chatbot artifacts file-based under `services/chatbot_service/chatbot/artifacts`.
- Use `user_service`'s `backfill_chatbot_behavior` command as the primary recovery path for `BehaviorEvent`.
- When changing models, add migrations and update `.env.example`, `docker-compose.yml`, `README.md`, and the relevant `AGENTS.md` files in the same change.

## Testing
- Run relevant tests in each touched service with `python manage.py test`.
- Add tests for new behavior when the touched service has a natural place for them.
- Do not change unrelated failing tests.
- When startup wiring changes, verify MySQL healthcheck + `bootstrap_mysql.py` for `user_service` and `order_service`, and PostgreSQL bootstrap for `product_service` and `chatbot_service`.
- Do not delete legacy service folders until `docker compose up --build -d` and smoke checks succeed for all 4 target services.
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
