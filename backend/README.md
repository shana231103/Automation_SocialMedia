# Automation Social Media - Backend

Hệ thống Backend tự động hóa đăng nhập và tương tác trên các nền tảng mạng xã hội (Facebook, YouTube, TikTok, Twitter) sử dụng **FastAPI**, **SQLAlchemy (PostgreSQL)**, **DrissionPage** và **Playwright**.

---

## 1. Tính năng nổi bật
- **API Đăng nhập Tự động**: Hỗ trợ đăng nhập tự động qua trình duyệt antidetect (như GemLogin, GoLogin,...) hoặc trình duyệt local thuần thông qua dòng lệnh.
- **Kiến trúc Linh hoạt & Đa Driver (Dependency Injection)**: Lớp dịch vụ tự động hóa giao tiếp qua Interface chung (`AutomationService`). Người dùng có thể dễ dàng chuyển đổi qua lại giữa **DrissionPage** và **Playwright** thông qua tệp cấu hình `.env` mà không ảnh hưởng tới code logic nghiệp vụ.
- **Tự động hóa an toàn (Context Manager)**: Đảm bảo đóng trình duyệt sạch sẽ và chụp ảnh màn hình lưu vết lỗi/kết quả khi phiên kết thúc hoặc xảy ra lỗi bất ngờ.
- **Luồng Server-Sent Events (SSE)**: Stream log thời gian thực từ backend về frontend để người dùng theo dõi tiến trình chạy kịch bản tự động hóa trực quan.

---

## 2. Cấu trúc Dự án
```text
backend/
├── app/
│   ├── application/        # Chứa Use Cases (Nghiệp vụ) và Interfaces trừu tượng
│   ├── domain/             # Chứa Entities (Models nghiệp vụ) và định nghĩa Repositories
│   ├── infrastructure/     # Cài đặt cụ thể Database (PostgreSQL), Repositories và Automation
│   │   ├── database/       # Cấu hình SQLAlchemy Connection, Models database, và Repositories
│   │   └── automation/     # Logic tự động hóa trình duyệt và quản lý vòng đời
│   │       ├── platforms_drissionpage/  # Kịch bản DrissionPage (FB, YT, TT, TW)
│   │       ├── platforms_playwright/    # Kịch bản Playwright (FB, YT, TT, TW)
│   │       ├── gemlogin_browser.py      # Bộ quản lý trình duyệt GemLogin (DrissionPage)
│   │       ├── local_browser.py         # Bộ quản lý trình duyệt local (DrissionPage)
│   │       ├── playwright_browser.py    # Bộ quản lý trình duyệt GemLogin & local (Playwright)
│   │       ├── drission_page.py         # Dịch vụ tự động hóa DrissionPage
│   │       └── playwright_service.py    # Dịch vụ tự động hóa Playwright
│   └── presentation/       # Lớp giao tiếp FastAPI endpoints (API Routes) và Schemas
├── docs/                   # Tài liệu hướng dẫn (Đào tạo refactoring, v.v.)
├── requirements.txt        # Các thư viện phụ thuộc của Python
├── test_automation.py      # Kịch bản kiểm thử tích hợp (Integration Test)
├── create_db.py            # Script khởi tạo cơ sở dữ liệu ban đầu
└── Makefile                # Tiện ích chạy nhanh các tác vụ phát triển
```

---

## 3. Hướng dẫn Cài đặt & Khởi chạy

### 3.1 Yêu cầu hệ thống
- Python 3.11 trở lên
- PostgreSQL Database đang chạy
- Ứng dụng GemLogin hoặc Google Chrome được cài đặt trên máy

### 3.2 Các bước thiết lập
1. **Clone mã nguồn và di chuyển vào thư mục backend**:
   ```bash
   cd backend
   ```
2. **Khởi tạo môi trường ảo (Virtual Environment)**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Trên macOS/Linux
   # Hoặc .venv\Scripts\activate trên Windows
   ```
3. **Cài đặt thư viện dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Cấu hình file môi trường `.env`**:
   Tạo file `.env` ở thư mục gốc của backend với nội dung tương tự sau:
   ```env
   # Chọn công cụ tự động hóa: playwright hoặc drissionpage
   AUTOMATION_PROVIDER=playwright

   DATABASE_URL=postgresql://postgres:password@localhost:5432/social_automation
   GEMLOGIN_API_URL=http://127.0.0.1:1010/api
   GEMLOGIN_PROFILE_NAME=default
   ```
5. **Khởi tạo các bảng cơ sở dữ liệu**:
   ```bash
   python create_db.py
   ```

### 3.3 Khởi chạy ứng dụng
Chạy server phát triển FastAPI (sử dụng Uvicorn):
```bash
uvicorn app.main:app --reload --port 8000
```
Server Swagger UI sẽ khả dụng tại địa chỉ: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 4. Kiểm thử (Testing)

### 4.1 Chạy Unit Test (Kiểm thử đơn vị cô lập)
Sử dụng bộ test giả lập (Mocking) không cần DB hay GemLogin thật:
```bash
python -m unittest discover -s .
```
*(Hoặc chạy qua Makefile: `make test`)*

### 4.2 Chạy Integration Test (Kiểm thử tích hợp)
Chạy thử kịch bản đăng nhập thực tế (Tự động đọc cấu hình driver từ file `.env`):
```bash
python test_automation.py
```
*(Hoặc chạy qua Makefile: `make test-integration`)*

---

## 5. Tài liệu Đào tạo Nhà phát triển Mới
Vui lòng tham khảo tài liệu [docs/browser_refactor_training.md](file:///Users/kyle/Desktop/Automation_SocialMedia-main/backend/docs/browser_refactor_training.md) để tìm hiểu sâu về:
- Cách hoạt động chi tiết của các lớp quản lý trình duyệt.
- Hướng dẫn cách tạo và tích hợp thêm trình duyệt mới (như GoLogin, ixBrowser).
- Kiến trúc Dependency Injection đã triển khai.
