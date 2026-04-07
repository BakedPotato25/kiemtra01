# kiemtra01 - Multi-Service Django Commerce (Docker)

Tài liệu này được viết để bạn có thể:

- Hiểu nhanh kiến trúc hệ thống
- Chạy demo ổn định
- Trả lời tốt trong buổi vấn đáp với giảng viên

README này đã được đối chiếu với code hiện tại (docker-compose, settings, urls, views, models, management commands).

## 1. Tổng quan nhanh

- Mô hình: 5 Django services + 2 database services trong Docker Compose
- Ngôn ngữ/nền tảng: Python 3.12, Django 5.2.x, Django REST Framework
- CSDL:
  - MySQL: customer_service, staff_service
  - PostgreSQL: laptop_service, mobile_service, accessory_service
- AI Chatbot:
  - Chat widget trong customer portal (dashboard + product detail)
  - Backend endpoint: `/customer/chatbot/reply/`
  - LLM provider: Gemini (`GEMINI_API_KEY`, `GEMINI_MODEL`)
  - Tự động fallback rule-based nếu không có key hoặc LLM lỗi
- Frontend chính:
  - Customer portal: http://localhost:8000/customer/login/
  - Staff portal: http://localhost:8003/staff/login/
- Product APIs (public read):
  - Laptop: http://localhost:8001/api/products/
  - Mobile: http://localhost:8002/api/products/
  - Accessory: http://localhost:8004/api/products/

## 2. Service matrix

| Service | Vai trò | DB | Host Port | Container Port |
|---|---|---|---:|---:|
| customer_service | Customer UI + đơn hàng + tổng hợp sản phẩm | MySQL customer_db | 8000 | 8000 |
| staff_service | Staff UI + CRUD sản phẩm qua API gateway | MySQL staff_db | 8003 | 8000 |
| laptop_service | Catalog API cho laptop | PostgreSQL laptop_db | 8001 | 8000 |
| mobile_service | Catalog API cho mobile | PostgreSQL mobile_db | 8002 | 8000 |
| accessory_service | Catalog API cho accessory | PostgreSQL accessory_db | 8004 | 8000 |
| mysql | DB server cho customer/staff | - | not published | 3306 |
| postgres | DB server cho các catalog services | - | not published | 5432 |

## 3. Kiến trúc và luồng giao tiếp

### 3.1 Luồng tổng quan

1. Customer đăng nhập vào customer_service
2. customer_service gọi 3 catalog APIs để tổng hợp danh sách sản phẩm
3. Customer add cart -> checkout (tạo order pending) -> pay (chuyển paid)
4. Staff đăng nhập vào staff_service
5. staff_service gọi catalog APIs để create/update/delete (có header X-Staff-Key)

### 3.2 Networking nội bộ Docker

Nội bộ Docker network phải dùng hostname có dấu gạch ngang:

- http://laptop-service:8000
- http://mobile-service:8000
- http://accessory-service:8000

Không dùng hostname có underscore (vì có thể gây HTTP 400 với Django service-to-service).

### 3.3 Bảo mật ghi dữ liệu catalog

- Đọc dữ liệu (GET): mở cho tất cả
- Ghi dữ liệu (POST/PUT/DELETE): catalog services kiểm tra header `X-Staff-Key`
- Key kỳ vọng: biến môi trường `STAFF_API_KEY` (mặc định: `dev-staff-key`)

### 3.4 Luồng nghiệp vụ chi tiết (Customer)

1. Customer login tại `/customer/login/` (chỉ tài khoản non-staff được vào customer portal)
2. Dashboard gọi 3 catalog APIs (`laptop/mobile/accessory`) qua `fetch_products`
3. Customer filter/search/sort và thao tác:
  - Add cart
  - Save item
  - Compare item (tối đa 4)
4. Customer vào product detail:
  - Xem gallery
  - Xem related products (`mixed` hoặc `similar`)
5. Checkout:
  - Tạo `Order(status=pending)` + `OrderItem` trong transaction atomic
  - Xóa cart sau khi tạo order
6. Pay order:
  - Chỉ order `pending` mới được pay
  - Update sang `paid`

### 3.5 Luồng nghiệp vụ chi tiết (Staff)

1. Staff login tại `/staff/login/` (port 8003)
2. Staff dashboard lấy danh sách sản phẩm từ 3 catalog services
3. Staff thực hiện Create/Update/Delete
4. staff_service gửi write request kèm header `X-Staff-Key`
5. Catalog service verify key qua `StaffWritePermission`

### 3.6 Luồng AI Chatbot (Customer portal)

1. Frontend widget nhận message từ user, gửi POST JSON đến `/customer/chatbot/reply/`
2. Backend bổ sung context:
  - `current_product` (nếu đang ở product detail)
  - user profile signal (`cart_items`, `saved_items`, `recent_paid_items`)
3. Hệ thống tạo recommendations từ catalog data:
  - Phát hiện category intent (laptop/mobile/accessory)
  - Ưu tiên sản phẩm còn hàng nếu user hỏi theo hướng in-stock
  - Rank theo token match, cùng category, gần brand/price
4. Hệ thống tạo prompt có context FAQ + recent blog + recommendation candidates
5. Nếu có `GEMINI_API_KEY`: gọi Gemini API để tạo câu trả lời
6. Nếu LLM gặp lỗi/không có key: trả lời fallback rule-based
7. Response trả về gồm:
  - `answer`
  - `recommendations` (tối đa 5)
  - `citations` (tối đa 3)
  - `source` (`gemini` hoặc `rule_based`)
  - `fallback_used`, `error_code`
8. Frontend render message + citations + recommendation cards; lưu history local theo user trong `localStorage`

## 4. Chi tiết từng service

### 4.1 customer_service (port 8000)

Chức năng chính:

- Đăng ký, đăng nhập, đăng xuất customer
- Dashboard tổng hợp sản phẩm từ 3 catalog services
- Filter/sort/search:
  - search theo tên/mô tả/brand
  - lọc theo category, brand, price range, stock
  - sắp xếp theo newest, price, tên
- Product detail theo `service_name` + `product_id`
- Product detail recommendations:
  - `mixed`: phối hợp 3 danh mục, ưu tiên category user đang quan tâm
  - `similar`: chỉ lấy trong cùng category với sản phẩm đang xem
- Saved items (lưu sản phẩm)
- Compare items (tối đa 4 sản phẩm)
- Cart -> Checkout -> Orders -> Pay
- Blog detail + testimonials
- AI Chatbot:
  - Nút chat nổi (floating widget)
  - Quick prompts (Under $1000, In Stock, Similar...)
  - Support EN/VI auto-detect
  - Có citation và recommendation cards
  - Có fallback khi LLM unavailable

Lưu ý nghiệp vụ quan trọng:

- Checkout tạo Order với status `pending`, tạo OrderItem từ CartItem, sau đó clear cart
- Pay chỉ cho phép khi order đang `pending`, thành công sẽ thành `paid`
- Order có sẵn status `cancelled` trong model (dự phòng mở rộng)

### 4.2 staff_service (port 8003)

Chức năng chính:

- Đăng ký, đăng nhập, đăng xuất staff
- Dashboard hiển thị tất cả sản phẩm (hoặc theo service filter)
- CRUD sản phẩm ở 3 catalog services
- Tự động gắn header `X-Staff-Key` khi gọi write APIs

Lưu ý:

- `/` của staff_service redirect sang `/staff/login/`
- Nếu đăng nhập tại port 8000 và vào `/staff/login/` sẽ 404 vì 8000 là customer_service

### 4.3 catalog services (laptop/mobile/accessory)

Chức năng chính:

- Expose REST API dưới `/api/products/`
- Cung cấp list/detail và CRUD Product
- Hỗ trợ query params: `search`, `brand`, `min_price`, `max_price`, `in_stock`

Model Product gồm các trường:

- id
- name
- brand
- description
- image_url
- price
- stock

## 5. URL map đầy đủ

### 5.1 Customer service (http://localhost:8000)

- `/` -> redirect theo trạng thái đăng nhập
- `/customer/login/`
- `/customer/register/`
- `/customer/logout/`
- `/customer/dashboard/`
- `/customer/saved/`
- `/customer/saved/toggle/` (POST)
- `/customer/compare/`
- `/customer/compare/toggle/` (POST)
- `/customer/compare/remove/<int:item_id>/` (POST)
- `/customer/blog/<slug:slug>/`
- `/customer/products/<str:service_name>/<int:product_id>/`
- `/customer/cart/`
- `/customer/cart/add/` (POST)
- `/customer/cart/remove/<int:item_id>/` (POST)
- `/customer/chatbot/reply/` (POST JSON)
- `/customer/checkout/` (POST)
- `/customer/orders/`
- `/customer/orders/<int:order_id>/pay/` (POST)

`service_name` hợp lệ: `laptop`, `mobile`, `accessory`.

### 5.2 Staff service (http://localhost:8003)

- `/` -> redirect `/staff/login/`
- `/staff/login/`
- `/staff/register/`
- `/staff/logout/`
- `/staff/dashboard/`

### 5.3 Catalog APIs

- Laptop base: http://localhost:8001/api/products/
- Mobile base: http://localhost:8002/api/products/
- Accessory base: http://localhost:8004/api/products/

Supported query params:

- `search`: tìm theo name/description/brand
- `brand`: lọc theo brand
- `min_price`: giá tối thiểu
- `max_price`: giá tối đa
- `in_stock`: `1|true|yes|on` để lấy hàng còn tồn

Ví dụ:

- `GET /api/products/?search=pro&brand=Lenovo&min_price=1000&max_price=2000&in_stock=true`

## 6. Dữ liệu và model quan trọng cho vấn đáp

### 6.1 customer_service models

- CartItem: giỏ hàng theo user + product_service + product_id (unique)
- Order: đơn hàng của user (`pending`, `paid`, `cancelled`)
- OrderItem: chi tiết sản phẩm trong đơn
- SavedItem: danh sách lưu sau
- CompareItem: danh sách so sánh
- BlogPost: bài viết nội dung
- Testimonial: đánh giá khách hàng

### 6.2 staff_service models

- Không có model nghiệp vụ riêng (dashboard staff thao tác qua API)

### 6.3 catalog models

- Product là model trung tâm cho mỗi catalog service

## 7. Biến môi trường (.env)

Tạo file `.env` từ `.env.example`:

```bash
copy .env.example .env
```

Biến quan trọng:

- Shared:
  - `STAFF_API_KEY`
- MySQL:
  - `MYSQL_ROOT_PASSWORD`
  - `CUSTOMER_MYSQL_DATABASE`, `CUSTOMER_MYSQL_USER`, `CUSTOMER_MYSQL_PASSWORD`
  - `STAFF_MYSQL_DATABASE`, `STAFF_MYSQL_USER`, `STAFF_MYSQL_PASSWORD`
- PostgreSQL:
  - `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Internal URLs:
  - `LAPTOP_SERVICE_URL=http://laptop-service:8000`
  - `MOBILE_SERVICE_URL=http://mobile-service:8000`
  - `ACCESSORY_SERVICE_URL=http://accessory-service:8000`
- AI Chatbot:
  - `GEMINI_API_KEY` (để trống nghĩa là chatbot chạy fallback)
  - `GEMINI_MODEL` (mặc định: `gemini-3-flash-preview`)

## 8. Runbook chạy project

### 8.1 Start

```bash
copy .env.example .env
docker compose up --build -d
```

### 8.2 Kiểm tra trạng thái

```bash
docker compose ps
docker compose logs -f customer_service
docker compose logs -f staff_service
```

### 8.3 Stop

```bash
docker compose down
```

Lệnh trên an toàn về dữ liệu (chỉ stop và remove containers/network, KHÔNG xóa volume).

Nếu bạn muốn tạm dừng nhanh mà không remove container:

```bash
docker compose stop
```

Khi cần mở lại nhanh sau `stop`:

```bash
docker compose start
```

Nếu cần reset toàn bộ volume DB (mất dữ liệu local):

```bash
docker compose down -v
```

### 8.4 Build lại an toàn để GIỮ NGUYÊN dữ liệu

Nguyên tắc:

- Dữ liệu DB đang nằm trong Docker volumes: `mysql_data`, `postgres_data`.
- Chỉ cần KHÔNG xóa volumes thì data sẽ còn sau khi build/recreate containers.

Quy trình khuyến nghị (full rebuild, giữ data):

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

Hoặc 1 lệnh nhanh:

```bash
docker compose up --build -d
```

### 8.5 Khi chỉ sửa 1 service (giữ data + rebuild nhanh)

Ví dụ chỉ sửa customer_service:

```bash
docker compose up -d --build customer_service
```

Ví dụ chỉ sửa staff_service:

```bash
docker compose up -d --build staff_service
```

### 8.6 NHỮNG LỆNH có thể làm mất dữ liệu (cảnh báo)

- `docker compose down -v` -> xóa volumes của project
- `docker volume rm ...` -> xóa volume chỉ định
- `docker system prune --volumes` -> có thể xóa volumes không được dùng

Nếu không muốn mất data, KHÔNG chạy các lệnh trên.

### 8.7 Backup nhanh trước khi rebuild lớn (khuyến nghị)

Backup MySQL:

```bash
docker compose exec mysql mysqldump -uroot -p$env:MYSQL_ROOT_PASSWORD --databases customer_db staff_db > mysql-backup.sql
```

Backup PostgreSQL:

```bash
docker compose exec postgres pg_dump -U postgres -d laptop_db > laptop-backup.sql
docker compose exec postgres pg_dump -U postgres -d mobile_db > mobile-backup.sql
docker compose exec postgres pg_dump -U postgres -d accessory_db > accessory-backup.sql
```

### 8.8 Quick checklist sau khi build lại

1. `docker compose ps` -> tất cả services phải `Up`
2. Đăng nhập lại customer/staff với tài khoản cũ
3. Kiểm tra products vẫn còn (API 8001/8002/8004)
4. Kiểm tra order cũ vẫn hiện trong customer_service
5. Nếu thiếu `accessory_db`, tạo tay 1 lần như mục troubleshooting

### 8.9 Quy trình chạy/tắt an toàn khuyến nghị cho demo

Trước demo:

```bash
docker compose up -d
docker compose ps
```

Nếu có sửa code và cần rebuild nhưng vẫn giữ dữ liệu:

```bash
docker compose up -d --build customer_service
docker compose up -d --build staff_service
docker compose up -d --build laptop_service
docker compose up -d --build mobile_service
docker compose up -d --build accessory_service
```

Sau demo, tắt an toàn:

```bash
docker compose down
```

Tuyệt đối KHÔNG dùng `down -v` trừ khi bạn chủ động chấp nhận mất data.

### 8.10 Kiểm tra nhanh AI Chatbot trước giờ demo

Kiểm tra key/model đã nạp vào customer_service:

```bash
docker compose exec customer_service python -c "import os; print('GEMINI_MODEL=' + os.getenv('GEMINI_MODEL','')); print('GEMINI_API_KEY_SET=' + ('1' if os.getenv('GEMINI_API_KEY') else '0'))"
```

Nếu `GEMINI_API_KEY_SET=0`, chatbot vẫn hoạt động ở fallback mode.

## 9. Migrate, seed, admin

### 9.1 Tạo superuser

```bash
docker compose exec customer_service python manage.py createsuperuser
docker compose exec staff_service python manage.py createsuperuser
```

### 9.2 Seed products (mỗi catalog)

```bash
docker compose exec laptop_service python manage.py seed_products --reset
docker compose exec mobile_service python manage.py seed_products --reset
docker compose exec accessory_service python manage.py seed_products --reset
```

### 9.3 Seed nội dung customer (blog + testimonials)

```bash
docker compose exec customer_service python manage.py seed_editorial_content --reset
```

## 10. Tài khoản đăng nhập theo từng port

Thông tin dưới đây là snapshot tài khoản hiện có trong DB (kiểm tra trực tiếp từ các container Django).

Lưu ý quan trọng:

- Django không cho đọc ngược plaintext password từ DB.
- Cột Password bên dưới là kết quả đã verify bằng check_password trên runtime hiện tại.
- Nếu bạn đổi password sau đó, hãy cập nhật lại bảng này cho đúng trạng thái mới.

### 10.1 Tài khoản hiện có (current snapshot)

| Service | Port | URL đăng nhập | Username | Email | Vai trò | Password |
|---|---:|---|---|---|---|---|
| customer_service | 8000 | http://localhost:8000/customer/login/ | customer1 | customer1@example.com | customer | 123456 |
| customer_service | 8000 | http://localhost:8000/customer/login/ | customer_demo | customer_demo@example.com | customer | 12345678 |
| customer_service | 8000 | http://localhost:8000/admin/ | admin_customer | admin_customer@example.com | admin (staff+superuser) | 123456 |
| staff_service | 8003 | http://localhost:8003/staff/login/ | staff1 | staff1@example.com | staff | 123456 |
| staff_service | 8003 | http://localhost:8003/staff/login/ | staff_demo | staff_demo@example.com | staff | 12345678 |
| staff_service | 8003 | http://localhost:8003/admin/ | admin_staff | admin_staff@example.com | admin (staff+superuser) | 123456 |
| laptop_service | 8001 | http://localhost:8001/admin/ | (none) | - | - | - |
| mobile_service | 8002 | http://localhost:8002/admin/ | (none) | - | - | - |
| accessory_service | 8004 | http://localhost:8004/admin/ | (none) | - | - | - |

### 10.2 Reset/đổi password nhanh để demo

```bash
docker compose exec customer_service python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.get(username='customer_demo'); u.set_password('Customer@123'); u.save(); print('customer_demo password reset')"

docker compose exec staff_service python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.get(username='staff_demo'); u.set_password('Staff@123'); u.save(); print('staff_demo password reset')"

docker compose exec customer_service python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.get(username='admin_customer'); u.set_password('Admin@123'); u.save(); print('admin_customer password reset')"

docker compose exec staff_service python manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.get(username='admin_staff'); u.set_password('Admin@123'); u.save(); print('admin_staff password reset')"
```

### 10.3 Tạo admin cho các catalog service (nếu cần)

```bash
docker compose exec laptop_service python manage.py createsuperuser
docker compose exec mobile_service python manage.py createsuperuser
docker compose exec accessory_service python manage.py createsuperuser
```

## 11. Demo script để đi vấn đáp (end-to-end + chatbot)

1. Mở customer login: http://localhost:8000/customer/login/
2. Mở staff login: http://localhost:8003/staff/login/
3. Đăng nhập staff, vào dashboard, tạo/sửa 1 product (ví dụ laptop)
4. Quay lại customer dashboard, refresh để thấy product đã đồng bộ
5. Demo filter/search/sort (q + brand + price + in stock)
6. Vào product detail, demo related products:
   - Mixed Recommendations
   - Similar Only
7. Demo chatbot ở dashboard:
   - 1 câu tiếng Việt
   - 1 câu tiếng Anh
   - Chỉ citations + recommendation cards
8. Demo chatbot ở product detail (có context current product)
9. Thêm vào cart -> checkout -> vào orders
10. Pay order và show status `pending -> paid`
11. Demo Saved/Compare (tối đa 4 items compare)

## 12. Prompt test nhanh cho AI Chatbot

Tiếng Việt:

- Tôi cần laptop dưới 1000 USD để học và lập trình
- Gợi ý phụ kiện cần mua thêm nếu tôi vừa mua laptop
- Sản phẩm nào còn hàng trong tầm giá 500-1000?

English:

- Recommend phones in stock under $900
- Suggest products similar to the one I am viewing
- What accessories should I buy with a laptop for office setup?

Expected khi demo:

- Có câu trả lời text rõ ràng
- Có recommendation cards
- Có citations
- Nếu không có GEMINI key: vẫn trả lời fallback không bị treo

## 13. Checklist trước buổi vấn đáp

- `docker compose ps` -> tất cả services `Up`
- Đăng nhập được customer (8000) và staff (8003)
- Seed data đã có (products + blog + testimonials)
- Staff tạo/sửa/xóa được sản phẩm
- Customer filter + đặt hàng được
- Có ít nhất 1 order đã `paid`
- Chatbot trả lời được (dù Gemini mode hoặc fallback mode)

## 14. Câu hỏi giảng viên thường hỏi + ý trả lời

### Q1. Vì sao tách 5 services thay vì 1 monolith?

- Tách theo bounded context: customer UI, staff UI, và 3 catalog domains
- Dễ scale/deploy độc lập, giảm coupling

### Q2. Vì sao customer/staff dùng MySQL còn catalog dùng PostgreSQL?

- Thể hiện polyglot persistence theo domain
- Customer/staff tập trung auth + order transaction
- Catalog APIs tối ưu cho đọc/lọc sản phẩm

### Q3. Có cơ chế bảo mật nào cho write APIs?

- Có. Catalog services bắt buộc `X-Staff-Key` cho POST/PUT/DELETE
- GET mở read-only

### Q4. Luồng checkout được đảm bảo tính nhất quán như thế nào?

- Dùng `transaction.atomic()`
- Tạo Order + bulk tạo OrderItems + clear Cart trong cùng giao dịch

### Q5. Nếu 1 product service bị down thì sao?

- customer/staff bắt `requests.RequestException`
- UI vẫn chạy, nhưng dữ liệu service đó có thể rỗng

### Q6. Tại sao URL nội bộ phải dùng dấu gạch ngang?

- Docker DNS hostname an toàn với hyphen
- underscore có thể gây lỗi host validation/HTTP 400

### Q7. Chatbot hoạt động như thế nào?

- Frontend gửi message đến `/customer/chatbot/reply/`
- Backend rank recommendations từ catalog data + context user
- Có Gemini mode (nếu có key) và fallback rule-based (nếu key thiếu/LLM lỗi)

### Q8. Chatbot lấy nguồn tham chiếu từ đâu?

- Từ product recommendations + context FAQ/dashboard
- Trả về danh sách citations để frontend render

## 15. Troubleshooting

### 15.1 404 `/staff/login/` khi đang ở port 8000

- Nguyên nhân: port 8000 là customer_service
- Cách đúng: http://localhost:8003/staff/login/

### 15.2 customer/staff không gọi được catalog services

- Kiểm tra URL nội bộ dùng hyphen hostnames:
  - `LAPTOP_SERVICE_URL=http://laptop-service:8000`
  - `MOBILE_SERVICE_URL=http://mobile-service:8000`
  - `ACCESSORY_SERVICE_URL=http://accessory-service:8000`

### 15.3 accessory_db bị thiếu

Nếu volume postgres đã tạo trước đó, script init có thể không chạy lại. Tạo DB thủ công:

```bash
docker compose exec postgres psql -U postgres -d postgres -c "CREATE DATABASE accessory_db;"
```

### 15.4 Write API bị 403

- Kiểm tra `STAFF_API_KEY` giống nhau giữa:
  - staff_service (client)
  - laptop/mobile/accessory services (server)

### 15.5 DB init scripts không cập nhật khi sửa file SQL

- `docker/*-init` chỉ chạy lần đầu khi volume mới được tạo
- Nếu buộc phải init lại toàn bộ: `docker compose down -v` rồi `up` (sẽ mất dữ liệu local)

### 15.6 Chatbot không gọi được LLM

- Kiểm tra `GEMINI_API_KEY` trong `.env`
- Kiểm tra đã rebuild/restart `customer_service` sau khi sửa env
- Nếu key chưa có, chatbot vẫn phải fallback và trả lời bình thường

### 15.7 Chatbot có text trả lời nhưng không có recommendations

- Có thể query quá hẹp hoặc service đang timeout
- Thử prompt rộng hơn (thêm category/budget)
- Kiểm tra products API 8001/8002/8004 có response

## 16. Quick command cheat sheet

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f

docker compose stop
docker compose start
docker compose down

docker compose exec customer_service python manage.py migrate
docker compose exec staff_service python manage.py migrate
docker compose exec laptop_service python manage.py migrate
docker compose exec mobile_service python manage.py migrate
docker compose exec accessory_service python manage.py migrate

docker compose exec laptop_service python manage.py seed_products --reset
docker compose exec mobile_service python manage.py seed_products --reset
docker compose exec accessory_service python manage.py seed_products --reset
docker compose exec customer_service python manage.py seed_editorial_content --reset

docker compose exec customer_service python -c "import os; print('GEMINI_MODEL=' + os.getenv('GEMINI_MODEL','')); print('GEMINI_API_KEY_SET=' + ('1' if os.getenv('GEMINI_API_KEY') else '0'))"
```

## 17. Ghi chú kỹ thuật bổ sung

- Mỗi service chạy trên `python:3.12-slim`
- Mỗi app container tự động `python manage.py migrate` trước khi runserver
- Main dependencies:
  - Django >=5.2,<5.3
  - djangorestframework 3.17.1
  - customer/staff: requests, PyMySQL, cryptography
  - catalog services: psycopg2-binary
- Chatbot implementation points:
  - UI widget + localStorage history trong customer frontend JS
  - Endpoint JSON: `/customer/chatbot/reply/`
  - Recommendation + ranking logic nằm ở customer service layer
  - LLM call đến Gemini API và fallback rule-based

## 18. Nếu mở chat mới với Copilot

Chỉ cần nói:

- Read README first.
- Đây là hệ thống 5 Django app services + 2 DB services trong Docker.
- Public ports: customer 8000, laptop 8001, mobile 8002, staff 8003, accessory 8004.
- Staff login phải dùng port 8003.
- Internal service URLs phải dùng hyphen hostnames (`*-service`).
- Chatbot endpoint là `/customer/chatbot/reply/`, có Gemini mode và fallback mode.
