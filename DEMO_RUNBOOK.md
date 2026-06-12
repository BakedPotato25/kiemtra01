# Demo Runbook - Kiemtra01 Commerce App

File nay dung de mo app nhanh truoc khi demo va bao cao tren truong. Cac lenh ben duoi gia dinh ban dang dung o thu muc root cua project:

```powershell
cd C:\Users\nguye\Desktop\kiemtra01
```

## 0. Quick Start Cho Demo Tinh Nang

Neu database va artifacts da seed tu lan truoc, start nhanh bang:

```powershell
docker compose config --quiet
docker compose up -d
docker compose ps -a
```

Sau do mo:

- Customer UI: `http://localhost:8080/customer/login/`
- Staff UI: `http://localhost:8080/staff/login/`
- Gateway dashboard: `http://localhost:8080/gateway/`
- Neo4j Browser: `http://localhost:7474/`

Login nhanh:

| Page | URL | Username | Password | Ghi chu |
|---|---|---|---|---|
| Customer | `http://localhost:8080/customer/login/` | `demo_customer` | `DemoPass123!` | Account customer chinh. |
| Customer | `http://localhost:8080/customer/login/` | `demo_customer_001` den `demo_customer_012` | `demo12345` | Synthetic customer co san order history cho staff demo. |
| Staff | `http://localhost:8080/staff/login/` | `demo_staff` | `StaffPass123!` | Account staff chinh. |

Neu demo tren database moi hoac muon refresh day du du lieu demo, chay block nay. Van dung `up -d`; chi doi sang `up --build -d` khi container loi, image thieu/cu, hoac vua doi Dockerfile/requirements:

```powershell
docker compose up -d

docker compose exec -T product_service python manage.py seed_products
docker compose exec -T user_service python manage.py seed_editorial_content

$createDemoAccounts = @'
from django.contrib.auth import get_user_model

User = get_user_model()
accounts = [
    ("demo_customer", "demo_customer@example.test", "DemoPass123!", False),
    ("demo_staff", "demo_staff@example.test", "StaffPass123!", True),
]
for username, email, password, is_staff in accounts:
    user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
    user.email = email
    user.is_staff = is_staff
    user.is_superuser = False
    user.is_active = True
    user.set_password(password)
    user.save()
print("ready: demo_customer / demo_staff")
'@
docker compose exec -T user_service python manage.py shell -c "$createDemoAccounts"

docker compose exec -T user_service python manage.py seed_staff_demo_data --customers 12 --min-orders 1 --max-orders 2
docker compose exec -T chatbot_service python manage.py build_chat_kb --max-products 160
docker compose exec -T chatbot_service python manage.py train_behavior_model
docker compose exec -T chatbot_service python manage.py import_behavior_graph --reset
```

Login nhanh sau khi chay block tren:

| Page | URL | Username | Password | Ghi chu |
|---|---|---|---|---|
| Customer | `http://localhost:8080/customer/login/` | `demo_customer` | `DemoPass123!` | Customer flow chinh luc demo. |
| Customer | `http://localhost:8080/customer/login/` | `demo_customer_001` den `demo_customer_012` | `demo12345` | Co order history de staff xem customers/orders. |
| Staff | `http://localhost:8080/staff/login/` | `demo_staff` | `StaffPass123!` | Staff dashboard/orders/items. |

## 1. Kiem Tra Truoc Khi Chay

Mo Docker Desktop truoc. Cho Docker bao dang chay on dinh, sau do kiem tra:

```powershell
docker version
docker compose config --quiet
```

Neu `.env` chua co, tao tu template:

```powershell
copy .env.example .env
```

Khong can tao service `api_gateway` rieng. Gateway hien tai gom:

- Nginx public gateway: `docker/gateway/nginx.conf`
- Docker Compose service: `gateway`
- Gateway registry/orchestration UI: `services/user_service/customer/api_gateway/`

## 2. Khoi Chay Full Stack

Chay toan bo service nhanh, khong build lai image:

```powershell
docker compose up -d
```

Chi build lai khi quick start loi, image thieu/cu, hoac vua sua Dockerfile/requirements:

```powershell
docker compose up --build -d
```

Kiem tra trang thai container:

```powershell
docker compose ps -a
```

Ket qua mong muon:

- `mysql`: healthy
- `postgres`: healthy
- `neo4j`: healthy
- `gateway`: up, port `8080`
- `user_service`: up, ports `8000`, `8003`
- `product_service`: up, port `8001`
- `order_service`: up, internal only
- `payment_service`: up, internal only
- `shipping_service`: up, internal only
- `chatbot_service`: up, port `8005`

Neu can xem log:

```powershell
docker compose logs --tail=120 gateway user_service product_service order_service payment_service shipping_service chatbot_service
```

Kiem tra Nginx gateway:

```powershell
docker compose exec -T gateway nginx -t
```

## 3. Chuan Bi Du Lieu Demo

Seed catalog 10 categories va 100 products:

```powershell
docker compose exec -T product_service python manage.py seed_products
```

Seed blog/testimonial cho customer UI:

```powershell
docker compose exec -T user_service python manage.py seed_editorial_content
```

Tao/cap nhat account demo co dinh cho customer page va staff page:

```powershell
$createDemoAccounts = @'
from django.contrib.auth import get_user_model

User = get_user_model()
accounts = [
    ("demo_customer", "demo_customer@example.test", "DemoPass123!", False),
    ("demo_staff", "demo_staff@example.test", "StaffPass123!", True),
]
for username, email, password, is_staff in accounts:
    user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
    user.email = email
    user.is_staff = is_staff
    user.is_superuser = False
    user.is_active = True
    user.set_password(password)
    user.save()
print("ready: demo_customer / demo_staff")
'@
docker compose exec -T user_service python manage.py shell -c "$createDemoAccounts"
```

Tao synthetic customer va order history cho staff Customers/Orders pages:

```powershell
docker compose exec -T user_service python manage.py seed_staff_demo_data --customers 12 --min-orders 1 --max-orders 2
```

Build chatbot knowledge base:

```powershell
docker compose exec -T chatbot_service python manage.py build_chat_kb --max-products 160
```

Train behavior model:

```powershell
docker compose exec -T chatbot_service python manage.py train_behavior_model
```

Import behavior graph vao Neo4j:

```powershell
docker compose exec -T chatbot_service python manage.py import_behavior_graph --reset
```

## 4. Smoke Check Nhanh Truoc Khi Demo

Chay cac request nhanh qua gateway chinh `http://localhost:8080`:

```powershell
Invoke-WebRequest http://localhost:8080/gateway/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8080/customer/login/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8080/staff/login/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8080/api/categories/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest http://localhost:8080/api/products/ | Select-Object -ExpandProperty StatusCode
```

Ket qua mong muon deu la `200`.

Kiem tra chatbot:

```powershell
Invoke-WebRequest `
  http://localhost:8080/api/chat/reply/ `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"message":"goi y laptop hoc tap","limit":3}' |
  Select-Object -ExpandProperty StatusCode
```

Ket qua mong muon: `200`.

Kiem tra API auth:

```powershell
$smokeUser = "demo_" + (Get-Date -Format "yyyyMMddHHmmss")
$authBody = @{
  username = $smokeUser
  email = "$smokeUser@example.test"
  password = "DemoPass123!"
  confirm_password = "DemoPass123!"
} | ConvertTo-Json

Invoke-WebRequest `
  http://localhost:8080/api/auth/register/ `
  -Method Post `
  -ContentType "application/json" `
  -Body $authBody |
  Select-Object -ExpandProperty StatusCode
```

Ket qua mong muon: `201`.

## 5. Tong Hop URL Cua App

Base URL nen dung khi demo:

- Public gateway: `http://localhost:8080`
- Neo4j Browser: `http://localhost:7474`
- Neo4j Bolt: `bolt://localhost:7687`

### 5.1 UI Va Gateway Pages

| Ten | URL |
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
| Staff product/items page | `http://localhost:8080/staff/items/` |
| Staff customers | `http://localhost:8080/staff/customers/` |
| Staff customer detail | `http://localhost:8080/staff/customers/<user_id>/` |
| Staff edit customer | `http://localhost:8080/staff/customers/<user_id>/edit/` |
| Staff toggle customer active | `http://localhost:8080/staff/customers/<user_id>/toggle-active/` |
| Staff reset customer password | `http://localhost:8080/staff/customers/<user_id>/reset-password/` |
| Staff orders | `http://localhost:8080/staff/orders/` |

### 5.2 Public API Qua Gateway

| Nhom | URL |
|---|---|
| Auth register | `http://localhost:8080/api/auth/register/` |
| Auth token | `http://localhost:8080/api/auth/token/` |
| Auth token refresh | `http://localhost:8080/api/auth/token/refresh/` |
| Auth current user | `http://localhost:8080/api/auth/me/` |
| Categories list/create | `http://localhost:8080/api/categories/` |
| Category detail | `http://localhost:8080/api/categories/<id>/` |
| Products list/create | `http://localhost:8080/api/products/` |
| Product detail | `http://localhost:8080/api/products/<id>/` |
| Cart list/create | `http://localhost:8080/api/cart/` |
| Cart item detail | `http://localhost:8080/api/cart/<item_id>/` |
| Saved list | `http://localhost:8080/api/saved/` |
| Saved toggle | `http://localhost:8080/api/saved/toggle/` |
| Compare list | `http://localhost:8080/api/compare/` |
| Compare toggle | `http://localhost:8080/api/compare/toggle/` |
| Compare item detail | `http://localhost:8080/api/compare/<item_id>/` |
| Checkout | `http://localhost:8080/api/checkout/` |
| Orders list/create | `http://localhost:8080/api/orders/` |
| Pay order | `http://localhost:8080/api/orders/<order_id>/pay/` |
| Staff orders API | `http://localhost:8080/api/staff/orders/` |
| Staff update shipping | `http://localhost:8080/api/staff/orders/<order_id>/shipping/` |
| Customer analytics | `http://localhost:8080/api/analytics/customers/` |
| Behavior source | `http://localhost:8080/api/internal/behavior-source/` |
| Payments list/create | `http://localhost:8080/api/payments/` |
| Payment detail | `http://localhost:8080/api/payments/<payment_id>/` |
| Payment by order | `http://localhost:8080/api/payments/by-order/<order_id>/` |
| Confirm payment | `http://localhost:8080/api/payments/<payment_id>/confirm/` |
| Cancel payment | `http://localhost:8080/api/payments/<payment_id>/cancel/` |
| Shipments list/create | `http://localhost:8080/api/shipments/` |
| Shipment detail | `http://localhost:8080/api/shipments/<shipment_id>/` |
| Shipment by order | `http://localhost:8080/api/shipments/by-order/<order_id>/` |
| Update shipment status | `http://localhost:8080/api/shipments/<shipment_id>/status/` |
| Chatbot reply | `http://localhost:8080/api/chat/reply/` |
| Chatbot behavior ingest | `http://localhost:8080/api/chat/ingest-behavior/` |

### 5.3 Direct Debug Ports

Chi dung cac URL nay khi gateway `8080` co van de hoac can debug service rieng:

| Service | URL |
|---|---|
| `user_service` root | `http://localhost:8000/` |
| `user_service` customer login | `http://localhost:8000/customer/login/` |
| `user_service` staff debug | `http://localhost:8003/staff/login/` |
| `product_service` categories | `http://localhost:8001/api/categories/` |
| `product_service` products | `http://localhost:8001/api/products/` |
| `chatbot_service` reply | `http://localhost:8005/api/chat/reply/` |
| `chatbot_service` behavior ingest | `http://localhost:8005/api/chat/ingest-behavior/` |

`order_service`, `payment_service`, va `shipping_service` la internal-only trong Compose, nen nen goi qua gateway hoac qua Docker network.

## 6. Demo Flow De Xuat

1. Mo `http://localhost:8080/gateway/`.
2. Giai thich gateway:
   - Nginx `gateway` nhan traffic o port `8080`.
   - `/customer/`, `/staff/`, `/api/auth/` di vao `user_service`.
   - `/api/products/`, `/api/categories/` di vao `product_service`.
   - `/api/cart/`, `/api/checkout/`, `/api/orders/` di vao `order_service`.
   - Payment/shipping/chat di vao service rieng.
3. Mo `http://localhost:8080/customer/login/` va login bang `demo_customer` / `DemoPass123!`.
4. Vao `customer/dashboard`, xem categories/products va block AI recommendation.
5. Them san pham vao cart.
6. Vao `customer/cart`, xem cart va goi y AI mua kem.
7. Checkout voi shipping info.
8. Vao `customer/orders`, bam pay order.
9. Mo `staff/login/` va login bang `demo_staff` / `StaffPass123!`, vao `staff/orders`.
10. Cap nhat shipping status: `preparing`, `shipped`, `delivered`.
11. Quay lai `customer/orders` de thay trang thai don hang da doi.
12. Mo chatbot widget va hoi: `Goi y laptop hoc tap`.
13. Mo Neo4j Browser neu can trinh bay graph behavior context.

## 7. Tai Khoan Demo

Tat ca account ben duoi dung qua gateway `http://localhost:8080`. Customer account chi login o customer page; staff account chi login o staff page. Superuser/admin account khong login o staff page, ma dung `/admin/`.

### 7.1 Customer Page

Login URL: `http://localhost:8080/customer/login/`

| Username | Password | Ghi chu |
|---|---|---|
| `demo_customer` | `DemoPass123!` | Account customer co dinh tao/cap nhat bang block Quick Start. |
| `demo_customer_001` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_002` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_003` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_004` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_005` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_006` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_007` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_008` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_009` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_010` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_011` | `demo12345` | Synthetic customer co order history cho staff demo. |
| `demo_customer_012` | `demo12345` | Synthetic customer co order history cho staff demo. |

Neu chay `seed_staff_demo_data --customers N`, command se tao username tu `demo_customer_001` den `demo_customer_NNN`. Password mac dinh cho synthetic customer moi tao la `demo12345`.

Ban van co the tao customer moi truc tiep o:

- URL: `http://localhost:8080/customer/register/`
- Password demo nen dung: `DemoPass123!`

Smoke check API auth o section 4 tao them account dang `demo_<timestamp>` voi password `DemoPass123!`; account nay la customer account, nhung username thay doi moi lan chay.

### 7.2 Staff Page

Login URL: `http://localhost:8080/staff/login/`

| Username | Password | Ghi chu |
|---|---|---|
| `demo_staff` | `StaffPass123!` | Account staff co dinh tao/cap nhat bang block Quick Start. |

Ban van co the tao staff moi truc tiep o:

- URL: `http://localhost:8080/staff/register/`
- Password demo nen dung: `StaffPass123!`

## 8. Kiem Tra Test Truoc Bao Cao

Chay toan bo test theo service:

```powershell
docker compose exec -T user_service python manage.py test customer staff
docker compose exec -T product_service python manage.py test catalog
docker compose exec -T order_service python manage.py test orders
docker compose exec -T payment_service python manage.py test payments
docker compose exec -T shipping_service python manage.py test shipments
docker compose exec -T chatbot_service python manage.py test chatbot
```

Ket qua gan nhat da pass:

- `user_service`: 28 tests
- `product_service`: 6 tests
- `order_service`: 11 tests
- `payment_service`: 5 tests
- `shipping_service`: 6 tests
- `chatbot_service`: 15 tests

## 9. Loi Thuong Gap

Neu Docker chua chay:

```powershell
Start-Service -Name com.docker.service
```

Neu gateway khong nhan route moi:

```powershell
docker compose restart gateway
docker compose exec -T gateway nginx -t
```

Neu service khong len:

```powershell
docker compose ps -a
docker compose logs --tail=160 <service_name>
```

Vi du:

```powershell
docker compose logs --tail=160 user_service
docker compose logs --tail=160 order_service
docker compose logs --tail=160 chatbot_service
```

Neu container loi vi image cu hoac dependency thay doi:

```powershell
docker compose up --build -d
```

Neu chatbot tra fallback hoac khong co goi y:

```powershell
docker compose exec -T chatbot_service python manage.py build_chat_kb --max-products 160
docker compose exec -T chatbot_service python manage.py train_behavior_model
docker compose exec -T chatbot_service python manage.py import_behavior_graph --reset
```

Neu catalog trong:

```powershell
docker compose exec -T product_service python manage.py seed_products
```

## 10. Tat App Sau Demo

Tat container nhung giu database volume:

```powershell
docker compose down
```

Khong dung `docker compose down -v` truoc demo hoac truoc khi nop bao cao, vi lenh do xoa database volumes.

## 11. Ghi Chu Cho Bao Cao

Kien truc hien tai la 6 application services cong Nginx gateway va database services:

- `user_service`: auth, customer UI, staff UI, gateway registry, chatbot proxy
- `product_service`: catalog
- `order_service`: cart, saved, compare, checkout, orders, analytics
- `payment_service`: payment lifecycle
- `shipping_service`: shipment lifecycle
- `chatbot_service`: AI reply, RAG, behavior model, Neo4j context
- `gateway`: Nginx public entrypoint on port `8080`
- `mysql`: user/order databases
- `postgres`: product/payment/shipping/chatbot databases
- `neo4j`: optional behavior graph

Diem can nhan manh khi bao cao:

- Khong co service rieng ten `api_gateway` vi Nginx gateway da xu ly public routing.
- `user_service/customer/api_gateway/` la noi luu metadata/registry de giai thich gateway trong UI.
- Cac service backend van giu boundary ro rang: catalog, order, payment, shipping, chatbot khong bi tron logic.
