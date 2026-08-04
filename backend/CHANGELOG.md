# Nhật ký thay đổi

Các thay đổi đáng chú ý của backend được ghi theo định dạng [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/).

## [1.4.0] - 2026-08-04

### Thêm mới

- Thêm batch login qua `/api/batch-login`, hỗ trợ giới hạn `MAX_CONCURRENT_LOGINS`, `MAX_BATCH_SIZE`, profile slot riêng và SSE multiplexed logs.
- Thêm `gemlogin_profile_name` cho từng tài khoản và gửi giá trị này từ frontend khi tạo tài khoản.
- Thêm AI selector fallback dùng ảnh chụp màn hình cùng DOM rút gọn để tìm lại ô đăng nhập qua Ollama local (`qwen3.5:9b`).
- Thêm endpoint `/api/ai/status` để kiểm tra AI fallback có sẵn hay không.
- Thêm unit test cho AI client, cancellation và các lỗi phân loại trạng thái của Facebook, TikTok, X và YouTube.

### Thay đổi

- Chuyển toàn bộ dependency Python sang `requirements.txt`; dự án không còn phụ thuộc vào UV hoặc cấu hình dependency trong `pyproject.toml`.
- Batch login loại bỏ ID trùng lặp, từ chối ID không hợp lệ và dùng database session riêng cho từng worker thread.
- `AutomationService.run_login` nhận thêm cancellation event tùy chọn; tín hiệu này được truyền qua `LoginAction` xuống platform flow.
- Thay các khoảng chờ không thể ngắt bằng cơ chế `wait_or_cancel`, giúp worker dừng sớm khi client SSE ngắt kết nối.
- Chuẩn hóa nhận diện trạng thái bằng hostname/path và tín hiệu UI cụ thể thay vì tìm substring trên toàn URL hoặc HTML.
- Log AI status verification hiển thị trạng thái dự đoán, confidence, lý do, bằng chứng hình ảnh/DOM và failure code đã được lọc dữ liệu nhạy cảm.

### Sửa lỗi

- Facebook: CAPTCHA/security challenge không còn bị nhận nhầm là tài khoản `dead` do từ `locked` trong HTML.
- Facebook: giảm ngân sách tìm credential selector, bỏ các lượt tìm lặp và báo rõ khi chuyển sang Ollama selector fallback.
- YouTube: URL Google Sign-In chứa `continue=https://www.youtube.com/` không còn bị nhận nhầm là đăng nhập thành công.
- X: query redirect chứa `/home` không còn bị nhận nhầm là đã đăng nhập.
- TikTok: URL `/foryou` khi chưa có profile UI không còn được xem là phiên đăng nhập hợp lệ.
- Sửa thống kê batch khi trạng thái thành công được trả về dưới dạng enum hoặc string.
- Tránh nạp SQLAlchemy session factory trong luồng đăng nhập đơn khi không cần thiết.

## [1.3.0] - 2026-07-03

### Thêm mới

- Thêm abstraction `AutomationPage` và `AutomationElement` dùng chung cho DrissionPage và Playwright.
- Thêm `AutomationAction`, `LoginAction` và `ACTION_REGISTRY` để điều phối action theo command pattern.
- Thêm unit test cho selector adapter, action registry và platform Facebook.

### Thay đổi

- Hợp nhất các platform script để không còn duy trì logic riêng cho từng browser driver.
- `DrissionPageAutomationService` và `PlaywrightAutomationService` dùng chung `BaseAutomationService` và action dispatcher.

### Loại bỏ

- Loại bỏ các thư mục platform trùng lặp dành riêng cho DrissionPage và Playwright.

## [1.2.0] - 2026-07-02

### Thêm mới

- Tích hợp Playwright cho Facebook, YouTube, TikTok và X.
- Thêm `AUTOMATION_PROVIDER` để lựa chọn DrissionPage hoặc Playwright.
- Tách giao diện Vue thành các component quản lý tài khoản, console và lịch sử.

### Thay đổi

- Tối ưu vòng lặp sự kiện Windows phục vụ tiến trình Playwright.

## [1.1.0] - 2026-06-25

### Thêm mới

- Thêm `BrowserContextManager`, `GemLoginBrowser` và `LocalBrowser` để quản lý vòng đời trình duyệt.
- Hỗ trợ inject browser manager factory vào automation service.
- Thêm Makefile, integration test và tài liệu backend ban đầu.

### Thay đổi

- Bao bọc phiên browser bằng context manager để giải phóng tài nguyên khi thành công, lỗi hoặc bị hủy.

## [1.0.0] - 2026-06-25

### Thêm mới

- Khởi tạo backend FastAPI.
- Thêm đăng nhập cơ bản cho Facebook, YouTube, TikTok và X bằng DrissionPage.
- Tích hợp PostgreSQL qua SQLAlchemy để lưu tài khoản và lịch sử.
- Thêm SSE để stream log thực thi.
