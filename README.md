# kiemtra01 - Multi-Service Django Commerce (Docker)

Tai lieu nay duoc cap nhat theo code hien tai: chatbot da tach thanh service rieng `chatbot_service`.

## 1. Tong quan nhanh

- Mo hinh: 6 Django services + 2 database services trong Docker Compose
- Nen tang: Python 3.12, Django 5.2.x, Django REST Framework
- CSDL:
  - MySQL: customer_service, staff_service
  - PostgreSQL: laptop_service, mobile_service, accessory_service
  - SQLite: chatbot_service (chi de luu metadata noi bo)
- AI Chatbot:
  - Frontend van goi endpoint customer: `/customer/chatbot/reply/`
  - customer_service chi dong vai tro proxy/gateway
  - chatbot_service xu ly RAG/recommendation/Gemma 4 31B (Google AI Studio key)/fallback tai `/api/chat/reply/`
- Frontend chinh:
  - Customer portal: http://localhost:8000/customer/login/
  - Staff portal: http://localhost:8003/staff/login/

## 2. Service matrix

| Service | Vai tro | DB | Host Port | Container Port |
|---|---|---|---:|---:|
| customer_service | Customer UI + don hang + tong hop san pham + proxy chatbot | MySQL customer_db | 8000 | 8000 |
| staff_service | Staff UI + CRUD san pham qua API gateway | MySQL staff_db | 8003 | 8000 |
| laptop_service | Catalog API cho laptop | PostgreSQL laptop_db | 8001 | 8000 |
| mobile_service | Catalog API cho mobile | PostgreSQL mobile_db | 8002 | 8000 |
| accessory_service | Catalog API cho accessory | PostgreSQL accessory_db | 8004 | 8000 |
| chatbot_service | Chatbot API (RAG + Gemma/Gemini + fallback) | SQLite | 8005 | 8000 |
| mysql | DB server cho customer/staff | - | not published | 3306 |
| postgres | DB server cho cac catalog services | - | not published | 5432 |

## 3. Kien truc va luong giao tiep

### 3.1 Luong tong quan

1. Customer dang nhap vao customer_service
2. customer_service goi 3 catalog APIs de tong hop danh sach san pham
3. Customer add cart -> checkout -> pay
4. Staff dang nhap vao staff_service va CRUD san pham qua catalog APIs
5. Frontend chat widget goi `/customer/chatbot/reply/`
6. customer_service:
  - tao user_context + user_ref
  - goi chatbot_service `/api/chat/reply/`
7. chatbot_service:
  - tu suy luan behavior signal trong chatbot engine
  - retrieve RAG context tu KB
  - goi LLM provider theo cau hinh env
  - fallback rule-based neu LLM loi/khong co key
  - tra ve answer + recommendations + citations

### 3.2 Networking noi bo Docker

Noi bo Docker network phai dung hostname co dau gach ngang:

- http://laptop-service:8000
- http://mobile-service:8000
- http://accessory-service:8000
- http://chatbot-service:8000

Khong dung hostname co underscore vi co the gay HTTP 400 voi service-to-service call.

### 3.3 Bao mat ghi du lieu catalog

- GET: mo cho tat ca
- POST/PUT/DELETE: catalog services kiem tra header `X-Staff-Key`
- Key mong doi: `STAFF_API_KEY` (mac dinh `dev-staff-key`)

## 4. Chi tiet tung service

### 4.1 customer_service (port 8000)

Chuc nang:

- Dang ky/dang nhap customer
- Dashboard tong hop 3 catalog services
- Saved/Compare/Cart/Checkout/Orders/Pay
- Product detail + related products (mixed/similar)
- Endpoint chatbot cho frontend: `/customer/chatbot/reply/`

Luu y:

- customer_service KHONG con chat engine local
- customer_service goi chatbot_service thong qua `CHATBOT_SERVICE_URL`

### 4.2 chatbot_service (port 8005)

Chuc nang:

- API: `POST /api/chat/reply/`
- Retrieve context tu KB (FAQ + product docs)
- Rank recommendations
- Goi LLM provider (mac dinh Gemma 4 31B qua Google AI Studio key)
- Fallback rule-based khi LLM unavailable
- Tra response JSON gom answer/recommendations/citations/source/fallback_used/error_code

### 4.3 staff_service (port 8003)

- Dang nhap staff
- CRUD san pham o 3 catalog services
- Tu dong gan `X-Staff-Key` cho write APIs

### 4.4 catalog services (laptop/mobile/accessory)

- API duoi `/api/products/`
- Ho tro query: `search`, `brand`, `min_price`, `max_price`, `in_stock`
- Model Product: id, name, brand, description, image_url, price, stock

## 5. URL map

### 5.1 Customer service (http://localhost:8000)

- `/customer/login/`
- `/customer/register/`
- `/customer/dashboard/`
- `/customer/products/<service>/<id>/`
- `/customer/cart/`
- `/customer/orders/`
- `/customer/chatbot/reply/` (POST JSON, frontend goi vao day)

### 5.2 Staff service (http://localhost:8003)

- `/staff/login/`
- `/staff/dashboard/`

### 5.3 Catalog APIs

- Laptop: http://localhost:8001/api/products/
- Mobile: http://localhost:8002/api/products/
- Accessory: http://localhost:8004/api/products/

### 5.4 Chatbot API

- Chatbot service base: http://localhost:8005/
- Endpoint: `POST /api/chat/reply/`
- Noi bo customer->chatbot: `http://chatbot-service:8000/api/chat/reply/`

### 5.5 Gateway manager (moi)

- Folder quan ly gateway: `services/customer_service/customer/api_gateway/`
- Web dashboard: http://localhost:8000/gateway/
- JSON index: http://localhost:8000/gateway/apis/
- Muc tieu: xem tap trung gateway routes cua customer_service + staff_service va mapping den upstream services.

## 6. Bien moi truong (.env)

Tao `.env` tu `.env.example`:

```bash
copy .env.example .env
```

Bien quan trong:

- Shared:
  - `STAFF_API_KEY`
- Product service URLs:
  - `LAPTOP_SERVICE_URL=http://laptop-service:8000`
  - `MOBILE_SERVICE_URL=http://mobile-service:8000`
  - `ACCESSORY_SERVICE_URL=http://accessory-service:8000`
- Chatbot routing:
  - `CHATBOT_SERVICE_URL=http://chatbot-service:8000`
- LLM provider:
  - `LLM_PROVIDER=gemma`
  - `GEMMA_MODEL=gemma-4-31b-it`
  - `GEMMA_TIMEOUT_SECONDS=45`
- Google AI Studio key (dung chung cho Gemma/Gemini):
  - `GEMINI_API_KEY`
- OpenRouter (optional, chi can khi `LLM_PROVIDER=openrouter`):
  - `OPENROUTER_API_KEY`
- Gemini (optional backup provider):
  - `CHATBOT_GEMINI_MODEL=gemini-3.1-flash-lite-preview`
  - `GEMINI_TIMEOUT_SECONDS=35`

## 7. Runbook nhanh

### 7.1 Start

```bash
copy .env.example .env
docker compose up --build -d
```

### 7.2 Kiem tra

```bash
docker compose ps
docker compose logs -f customer_service
docker compose logs -f chatbot_service
```

### 7.3 Stop

```bash
docker compose down
```

## 8. Migrate, seed, chatbot setup

### 8.1 Migrate

```bash
docker compose exec customer_service python manage.py migrate
docker compose exec staff_service python manage.py migrate
docker compose exec laptop_service python manage.py migrate
docker compose exec mobile_service python manage.py migrate
docker compose exec accessory_service python manage.py migrate
docker compose exec chatbot_service python manage.py migrate
```

### 8.2 Seed products + content

```bash
docker compose exec laptop_service python manage.py seed_products --reset
docker compose exec mobile_service python manage.py seed_products --reset
docker compose exec accessory_service python manage.py seed_products --reset
docker compose exec customer_service python manage.py seed_editorial_content --reset
```

### 8.3 Build chatbot KB (service moi)

```bash
docker compose exec chatbot_service python manage.py build_chat_kb --max-products 160
```

Hoac dung script dong bo tu dong (build KB + train behavior model + copy artifacts ve host + xoa copy customer):

```powershell
./scripts/sync-chatbot-kb.ps1
```

Hoac chay task trong VS Code:

- `chatbot: sync chatbot artifacts`
- `chatbot: rebuild + sync artifacts`

Artifact sau khi dong bo:

- `services/chatbot_service/chatbot/artifacts/knowledge_base.json`
- `services/chatbot_service/chatbot/artifacts/model_behavior.json`

### 8.4 Train model_behavior (chatbot_service)

```bash
docker compose exec chatbot_service python manage.py train_behavior_model --epochs 120 --lr 0.02
```

### 8.5 Kiem tra LLM config da nap cho chatbot_service

```bash
docker compose exec chatbot_service python -c "import os; print('LLM_PROVIDER=' + os.getenv('LLM_PROVIDER','')); print('GEMMA_MODEL=' + os.getenv('GEMMA_MODEL','')); print('OPENROUTER_API_KEY_SET=' + ('1' if os.getenv('OPENROUTER_API_KEY') else '0')); print('GEMINI_API_KEY_SET=' + ('1' if os.getenv('GEMINI_API_KEY') else '0'))"
```

Neu `GEMINI_API_KEY_SET=0` (khi `LLM_PROVIDER=gemma`), chatbot se tra loi fallback.

## 9. Luong demo ngan (end-to-end)

1. Dang nhap staff va tao/sua 1 product
2. Quay customer dashboard de thay du lieu cap nhat
3. Vao product detail, test related products
4. Mo chat widget:
   - hoi 1 cau tieng Viet
   - hoi 1 cau tieng Anh
5. Add cart -> checkout -> pay
6. Xac nhan chatbot response co recommendations + citations

## 10. Troubleshooting

### 10.1 staff login 404 tren port 8000

- Dung sai service. Staff dung port 8003.

### 10.2 customer khong goi duoc chatbot_service

- Kiem tra `CHATBOT_SERVICE_URL`
- Kiem tra `docker compose ps` co `chatbot_service` dang Up
- Kiem tra logs chatbot:

```bash
docker compose logs -f chatbot_service
```

### 10.3 Write API bi 403

- Kiem tra `STAFF_API_KEY` giua staff_service va catalog services

### 10.4 Chatbot khong goi duoc LLM provider

- Kiem tra `LLM_PROVIDER` trong `.env`
- Neu `LLM_PROVIDER=gemma`: kiem tra `GEMINI_API_KEY`, `GEMMA_MODEL`
- Neu `LLM_PROVIDER=openrouter`: kiem tra `OPENROUTER_API_KEY`, `GEMMA_MODEL`
- Neu `LLM_PROVIDER=gemini`: kiem tra `GEMINI_API_KEY`, `GEMINI_MODEL`
- Rebuild service sau khi sua env:

```bash
docker compose up -d --build chatbot_service customer_service
```

## 11. Ghi chu quan trong cho bao cao

- Kien truc hien tai da tach chatbot thanh microservice rieng.
- Frontend khong can doi endpoint: van goi `/customer/chatbot/reply/`.
- customer_service dong vai tro gateway/proxy.
- chatbot_service xu ly behavior + RAG + LLM + fallback.
