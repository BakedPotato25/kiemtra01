# AI Chatbot Implementation Notes (For Report)

## 1. Scope completed in current project

Current architecture is fully separated:

- `customer_service` keeps customer UI/business flow and proxies chat requests.
- `chatbot_service` owns chatbot engine end-to-end: behavior model, KB, RAG, Gemini, fallback.
- Frontend endpoint remains unchanged: `/customer/chatbot/reply/`.

## 2. Service separation

### 2.1 customer_service responsibilities

- Collect request input from widget.
- Build user context (`cart_items`, `saved_items`, `recent_paid_items`).
- Forward request to `chatbot_service` with `user_ref`, `current_product`, `user_context`.
- Return normalized response for frontend rendering.

### 2.2 chatbot_service responsibilities

- API endpoint: `POST /api/chat/reply/`
- Behavior event logging (`BehaviorEvent`) in chatbot DB.
- Behavior signal inference (`model_behavior`) in chatbot service.
- Knowledge Base build/load and retrieval.
- RAG prompt construction.
- Gemini generation + rule-based fallback.
- Return `answer`, `recommendations`, `citations`, `source`, `fallback_used`, `error_code`.

## 3. Behavior model ownership (moved)

Behavior model has been moved completely to `chatbot_service`.

- Behavior model code: `services/chatbot_service/chatbot/behavior_ai.py`
- Behavior event model: `services/chatbot_service/chatbot/models.py`
- Training command: `services/chatbot_service/chatbot/management/commands/train_behavior_model.py`
- Model artifact: `services/chatbot_service/chatbot/artifacts/model_behavior.json`

Customer-side behavior engine files were removed.

## 4. Knowledge Base ownership

Knowledge Base build logic is in `chatbot_service`:

- KB module: `services/chatbot_service/chatbot/rag_kb.py`
- Build command: `services/chatbot_service/chatbot/management/commands/build_chat_kb.py`
- Main artifact: `services/chatbot_service/chatbot/artifacts/knowledge_base.json`
- Automation script: `scripts/sync-chatbot-kb.ps1` (build KB + sync artifact + remove customer copy by default)

## 5. Commands used

From repository root:

1. `docker compose up -d --build chatbot_service customer_service`
2. `docker compose exec customer_service python manage.py migrate`
3. `docker compose exec chatbot_service python manage.py migrate`
4. `docker compose exec chatbot_service python manage.py build_chat_kb --max-products 160`
5. `docker compose exec chatbot_service python manage.py train_behavior_model --epochs 120 --lr 0.02`
6. `./scripts/sync-chatbot-kb.ps1`

## 6. Validation evidence

- `customer_service` can successfully call `http://chatbot-service:8000/api/chat/reply/`.
- `chatbot_service` `BehaviorEvent` rows increase after chat requests.
- `train_behavior_model` runs successfully in `chatbot_service` and writes model artifact.

## 7. Gemini settings

Gemini settings remain unchanged:

- `GEMINI_API_KEY`
- `GEMINI_MODEL`

No variable rename or key/model replacement was done.
