# Demo Script End-to-End (E-commerce + AI Chatbot)

## 1) Muc tieu demo
- Chung minh he thong e-commerce da hoan chinh luong mua hang.
- Chung minh chatbot AI hoat dong tren customer portal, tra loi tu van va goi y san pham.
- Chung minh co nguon tham chieu (citation) va co fallback khi LLM gap su co.

## 2) KPI noi bo da chot
- Task completion >= 75%
- Recommendation usefulness >= 80%
- Latency <= 6 giay
- Fallback = 100%

## 3) Chuan bi truoc gio demo (2-3 phut)
1. Chay:
   - docker compose up -d --build customer_service
2. Kiem tra trang thai:
   - docker compose ps
3. Kiem tra key LLM da nap vao customer_service:
   - docker compose exec customer_service python -c "import os; print('GEMINI_MODEL=' + os.getenv('GEMINI_MODEL','')); print('GEMINI_API_KEY_SET=' + ('1' if os.getenv('GEMINI_API_KEY') else '0'))"

## 4) Tai khoan demo su dung
- Customer portal (http://localhost:8000/customer/login/)
  - customer1 / 123456
  - customer_demo / 12345678
- Staff portal (http://localhost:8003/staff/login/)
  - staff1 / 123456
  - staff_demo / 12345678

## 5) Flow demo tu dau den cuoi (goi y 8-10 phut)
1. Mo customer login va staff login o 2 tab rieng.
2. Dang nhap staff, vao dashboard, tao hoac sua 1 san pham (de chung minh quan tri).
3. Quay ve customer dashboard, refresh, chung minh san pham da thay doi.
4. Demo filter/search tren customer dashboard.
5. Mo product detail cua 1 san pham bat ky.
6. Chi khu "Recommended Products You May Need" ben duoi product detail.
7. Mo chatbot tren dashboard:
   - Hoi 1 cau tieng Viet ve tu van mua hang.
   - Hoi 1 cau tieng Anh ve recommendation.
   - Chi phan Sources/Citations ngay duoi cau tra loi.
8. Mo chatbot tren product detail:
   - Hoi "goi y san pham tuong tu" de chung minh context theo san pham dang xem.
9. Them san pham vao cart -> checkout -> vao orders -> pay.
10. Ket luan: he thong bao gom luong nghiep vu + AI assistant + fallback an toan.

## 6) Bo cau hoi de test KPI nhanh
- Dung file: .github/prompts/chatbot-demo-test-prompts.prompt.md
- Cach cham nhanh:
  - Task completion: danh dau Dat/Khong dat cho 20 prompt.
  - Recommendation usefulness: moi prompt recommendation co >=1 item hop le.
  - Latency: canh thoi gian tra loi trung binh.
  - Fallback: tat key LLM tam thoi va test 2 prompt, phai van tra loi.

## 7) Nhanh gon de phong su co
- Neu LLM bi rate-limit: van demo fallback + recommendation rule-based.
- Neu staff login 404: nhac lai staff phai vao port 8003.
- Neu chat khong tra loi: check customer_service logs va GEMINI_API_KEY_SET.

## 8) One-liner ket thuc bai bao ve
"He thong da dat muc tieu demo: chat tu van song ngu, recommendation hoat dong o dashboard va product detail, co citation nguon, va co fallback de dam bao tinh on dinh khi LLM su co."