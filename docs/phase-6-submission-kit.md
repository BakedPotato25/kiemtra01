# Phase 6 Submission Kit

This checklist keeps the submission pack fast to assemble after the Phase 6 demo.

## 1. Existing artifacts from earlier phases

| Evidence | Primary file | Notes for PDF caption |
|---|---|---|
| 20-row dataset sample | `services/chatbot_service/chatbot/artifacts/data_user500_sample20.csv` | Use as the compact sample from the generated 500-user behavior dataset. |
| Dataset stats | `services/chatbot_service/chatbot/artifacts/dataset_stats.json` | Useful for user/event/session counts when writing the methodology slide/page. |
| Metric comparison table | `services/chatbot_service/chatbot/artifacts/metrics_comparison.csv` | Compare RNN/LSTM/BiLSTM scores in one table. |
| Best-model note | `services/chatbot_service/chatbot/artifacts/model_best_reason.txt` | Explains which model was selected and why. |
| Confusion matrix | `services/chatbot_service/chatbot/artifacts/confusion_matrix_rnn.png` | Use the model that matches `model_best_reason.txt`; swap to `lstm` or `bilstm` if needed. |
| Training history plot | `services/chatbot_service/chatbot/artifacts/history_rnn.png` | Pair with the same model family used for the confusion matrix. |
| Neo4j graph image | `services/chatbot_service/chatbot/artifacts/behavior_graph_demo.svg` | Show this together with the Cypher/browser screenshot if available. |
| Graph notes / Cypher | `docs/neo4j_behavior_graph.md`, `docs/neo4j_behavior_graph_queries.cypher` | Use for appendix or speaker notes. |
| Kaggle / training note | `docs/phase-3-kaggle-training-2a.md` | Reuse short text for the Phase 3 evidence section. |

## 2. UI screenshots to capture for Phase 6

Save these images under `docs/evidence/screenshots/` so the PDF pack has a stable location:

| Screenshot | Target path | What should be visible |
|---|---|---|
| Dashboard AI suggestions | `docs/evidence/screenshots/dashboard-ai.png` | Search/filter toolbar, product results, and the `AI goi y cho ban` block in one frame. |
| Cart AI suggestions | `docs/evidence/screenshots/cart-ai.png` | Cart rows, order summary, and the `Co the mua kem` block in one frame. |
| Chat widget | `docs/evidence/screenshots/chat-widget.png` | Existing floating widget open with an answer, recommendation cards, and citations/source chips if available. |
| Neo4j Browser | `docs/evidence/screenshots/neo4j-browser.png` | Browser graph view or query result proving the behavior graph import. |

## 3. Suggested PDF structure

1. Architecture / 4-service overview
2. Phase 2 dataset sample and generated statistics
3. Phase 3 model comparison table plus confusion matrix/history plot
4. Phase 4 Neo4j behavior graph image and short explanation
5. Phase 5 chatbot retrieval flow and widget screenshot
6. Phase 6 dashboard AI block and cart AI block integrated into the live e-commerce UI

## 4. Demo script

1. `docker compose up --build -d`
2. Sign in at `http://localhost:8000/customer/login/`
3. Search on `/customer/dashboard/` and capture the AI block
4. Add item(s) to cart and capture the cart AI block
5. Open the chat widget and capture one answer
6. Open Neo4j Browser at `http://localhost:7474/` and capture the graph

## 5. Short captions you can reuse

- "Generated 20-row sample extracted from the 500-user synthetic behavior dataset."
- "Model comparison across RNN, LSTM, and BiLSTM used to choose the best next-category predictor."
- "Confusion matrix and training history for the selected behavior model."
- "Neo4j behavior graph used as an optional retrieval layer in the chatbot pipeline."
- "Dashboard search results extended with AI product suggestions without changing the customer route."
- "Cart flow extended with buy-together AI recommendations while keeping the original checkout layout."
- "Existing floating chat widget preserved and connected to the Phase 5 hybrid chatbot backend."
