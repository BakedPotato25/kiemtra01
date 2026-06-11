# chatbot_service

`chatbot_service` is the AI backend for chat replies, recommendations, behavior ingest, file-based RAG, behavior model artifacts, optional Neo4j graph context, and PostgreSQL-backed behavior persistence.

## Runtime

- Compose service: `chatbot_service`
- Docker hostname: `chatbot-service`
- Debug port: `8005`
- Public gateway path: `/api/chat/`
- Database: PostgreSQL `chatbot_db`
- Optional graph store: Neo4j via `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`

## Key Routes

- `POST /api/chat/reply/`
- `POST /api/chat/ingest-behavior/`

The customer UI calls this service through `user_service` at `/customer/chatbot/reply/`.

## Artifacts

Runtime artifacts are file-based and bind-mounted from `chatbot/artifacts/`. Important files include:

- `knowledge_base.json`
- `model_behavior.json`
- `model_best.keras`
- `label_encoder.json`
- `tokenizer_or_vocab.json`
- `training_data_behavior.json`
- `behavior_graph_demo.svg`

## Commands

```bash
python bootstrap_postgres.py
python manage.py migrate
python manage.py build_chat_kb --max-products 160
python manage.py train_behavior_model
python manage.py import_behavior_graph --reset
python manage.py test chatbot
```

