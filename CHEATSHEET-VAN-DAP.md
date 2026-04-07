# CHEATSHEET VẤN ĐÁP - kiemtra01

Mục tiêu: ôn cực nhanh trong 5-10 phút trước khi vào phòng vấn đáp.

## 1) Bản giới thiệu 30 giây

- Đây là hệ thống Django microservices chạy bằng Docker Compose.
- Có 5 app services + 2 database services.
- customer_service và staff_service dùng MySQL.
- laptop/mobile/accessory services dùng PostgreSQL.
- staff_service CRUD sản phẩm qua catalog APIs (có `X-Staff-Key`).
- customer_service tổng hợp sản phẩm từ 3 catalog services, hỗ trợ cart -> checkout -> pay.
- Customer portal có AI Chatbot: tư vấn sản phẩm, gợi ý, và fallback khi LLM lỗi.

## 2) Nhớ nhanh port

- 8000: customer
- 8001: laptop API
- 8002: mobile API
- 8003: staff
- 8004: accessory API

Ghi nhớ: staff luôn là 8003, không phải 8000.

## 3) URL quan trọng

Customer:
- http://localhost:8000/customer/login/
- http://localhost:8000/customer/dashboard/
- http://localhost:8000/customer/cart/
- http://localhost:8000/customer/orders/
- http://localhost:8000/customer/chatbot/reply/ (POST)

Staff:
- http://localhost:8003/staff/login/
- http://localhost:8003/staff/dashboard/

Catalog APIs:
- http://localhost:8001/api/products/
- http://localhost:8002/api/products/
- http://localhost:8004/api/products/

## 4) Luồng nghiệp vụ cần thuộc

Luồng customer:
1. Đăng nhập customer
2. Dashboard lấy data từ 3 catalog services
3. Filter/search/sort, add cart, save, compare
4. Checkout tạo order `pending`
5. Pay order chuyển `pending -> paid`

Luồng staff:
1. Đăng nhập staff
2. Tạo/sửa/xóa product trên dashboard
3. staff_service gọi API đến catalog services kèm `X-Staff-Key`

Luồng AI Chatbot:
1. User gửi câu hỏi từ widget
2. Backend gom context (current product + user signals)
3. Gợi ý recommendations từ catalog
4. Nếu có `GEMINI_API_KEY` thì gọi Gemini
5. Nếu không có key hoặc lỗi mạng thì fallback rule-based

## 5) Bảo mật write API

- Catalog services cho GET tự do.
- POST/PUT/DELETE bắt buộc header `X-Staff-Key`.
- Giá trị key đọc từ `STAFF_API_KEY`.

## 6) Query filters catalog API

- `search`
- `brand`
- `min_price`
- `max_price`
- `in_stock` (`1/true/yes/on`)

Ví dụ:
`GET /api/products/?search=pro&brand=Lenovo&min_price=1000&max_price=2000&in_stock=true`

## 7) Lệnh chạy nhanh và an toàn dữ liệu

Start:
`docker compose up --build -d`

Kiểm tra:
`docker compose ps`

Logs:
`docker compose logs -f customer_service`

Seed data:
- `docker compose exec laptop_service python manage.py seed_products --reset`
- `docker compose exec mobile_service python manage.py seed_products --reset`
- `docker compose exec accessory_service python manage.py seed_products --reset`
- `docker compose exec customer_service python manage.py seed_editorial_content --reset`

Tắt an toàn (không mất data):
`docker compose down`

Tạm dừng nhanh:
`docker compose stop`

Mở lại nhanh:
`docker compose start`

Cảnh báo mất dữ liệu:
- `docker compose down -v`
- `docker system prune --volumes`

## 8) Kiểm tra chatbot trước demo

Lệnh kiểm tra key/model trong customer_service:

`docker compose exec customer_service python -c "import os; print('GEMINI_MODEL=' + os.getenv('GEMINI_MODEL','')); print('GEMINI_API_KEY_SET=' + ('1' if os.getenv('GEMINI_API_KEY') else '0'))"`

Nếu `GEMINI_API_KEY_SET=0`: chatbot vẫn phải chạy fallback.

## 9) Lỗi thường gặp và cách trả lời

1. 404 `/staff/login/` trên port 8000:
- Vì 8000 là customer_service.
- Dùng đúng port 8003 cho staff.

2. customer/staff gọi catalog lỗi:
- Kiểm tra URL nội bộ phải dùng hyphen hostname:
  - http://laptop-service:8000
  - http://mobile-service:8000
  - http://accessory-service:8000

3. accessory_db bị thiếu:
- Tạo tay trong postgres container:
`docker compose exec postgres psql -U postgres -d postgres -c "CREATE DATABASE accessory_db;"`

4. Write API 403:
- `STAFF_API_KEY` giữa staff_service và catalog services không trùng.

5. Chatbot không trả lời bằng Gemini:
- Kiểm tra `GEMINI_API_KEY`.
- Nếu chưa có key, trình bày là chatbot đang chạy fallback mode.

## 10) 8 câu hỏi có thể bị hỏi

1. Tại sao tách microservices?
- Tách bounded context, dễ scale/deploy độc lập.

2. Tại sao dùng cả MySQL và PostgreSQL?
- Thể hiện polyglot persistence theo domain.

3. Làm sao đảm bảo checkout nhất quán?
- Dùng `transaction.atomic()` khi tạo order + order items.

4. Nếu 1 catalog service down thì sao?
- Bắt exception requests, UI vẫn chạy nhưng data service đó có thể rỗng.

5. Bảo mật thao tác ghi như nào?
- `X-Staff-Key` + `STAFF_API_KEY` cho write methods.

6. Tại sao không dùng underscore hostname?
- Có thể gây host validation/HTTP 400 trong inter-service call.

7. Chatbot hoạt động như nào?
- Có Gemini mode và fallback mode, luôn ưu tiên trải nghiệm không bị “treo”.

8. Chatbot dựa vào dữ liệu nào để gợi ý?
- Catalog products + context user + context current product + FAQ/blog snippets.

## 11) Script demo 3-5 phút

1. Mở 2 tab:
- customer login (8000)
- staff login (8003)

2. Đăng nhập staff, tạo/sửa 1 product.

3. Quay customer dashboard, refresh và cho thấy dữ liệu vừa cập nhật.

4. Demo filter/search + in_stock.

5. Vào product detail, demo recommendations (mixed/similar).

6. Demo chatbot:
- 1 câu tiếng Việt
- 1 câu tiếng Anh
- chỉ citations + recommendation cards

7. Add cart -> checkout -> pay, mở orders để show `pending -> paid`.

## 12) 60 giây trước khi vào phòng

- `docker compose ps`: tất cả services Up
- Nhớ đúng port 8003 cho staff
- Nhớ `X-Staff-Key` chỉ cho write API
- Nhớ luồng `pending -> paid`
- Nhớ 3 hostname nội bộ có dấu gạch ngang
- Nhớ chatbot có fallback (nếu không có Gemini key vẫn demo được)

Chúc bạn vấn đáp tốt.