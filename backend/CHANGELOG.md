# Nhật ký thay đổi (Changelog)

Mọi thay đổi lớn đối với dự án này sẽ được ghi nhận và cập nhật trong file này theo định dạng [Keep a Changelog](https://keepachangelog.com/vi/1.0.0/).

---

## [1.1.0] - 2026-06-25

### Thêm mới (Added)
- **Interface `BrowserContextManager`**: Định nghĩa giao diện tiêu chuẩn cho các dịch vụ quản lý trình duyệt tự động hóa kịch bản, kế thừa cơ chế Context Manager của Python (`__enter__`, `__exit__`).
- **Module `GemLoginBrowser`**: Tách logic điều khiển trình duyệt qua GemLogin API thành lớp context manager độc lập trong file [gemlogin_browser.py](file:///Users/kyle/Desktop/Automation_SocialMedia-main/backend/app/infrastructure/automation/gemlogin_browser.py).
- **Module `LocalBrowser`**: Hỗ trợ khởi chạy và tắt trực tiếp trình duyệt Chrome local thông qua dòng lệnh bằng cách quản lý tiến trình hệ thống qua `subprocess` trong file [local_browser.py](file:///Users/kyle/Desktop/Automation_SocialMedia-main/backend/app/infrastructure/automation/local_browser.py).
- **Dependency Injection (DI) cho Automation Service**: Cập nhật `DrissionPageAutomationService` cho phép nhận vào một factory của `BrowserContextManager` từ bên ngoài để dễ dàng mở rộng sang các dịch vụ trình duyệt khác (GoLogin, ixBrowser, GinLogin,...).
- **Bộ Unit Test Đơn Vị Cô Lập**: Thiết lập bộ unit test [test_gemlogin_browser.py](file:///Users/kyle/.gemini/antigravity-ide/brain/daad858c-9472-4203-84bf-7cd843eb79b6/scratch/test_gemlogin_browser.py) bằng Mocking để chạy kiểm thử mà không cần cài đặt database hay bật trình duyệt thực tế.
- **Tài liệu đào tạo**: Tài liệu kỹ thuật chi tiết bằng tiếng Việt [docs/browser_refactor_training.md](file:///Users/kyle/Desktop/Automation_SocialMedia-main/backend/docs/browser_refactor_training.md) dùng để đào tạo các nhà phát triển mới của dự án.
- **Makefile & README.md**: Bổ sung tệp tin hỗ trợ chạy nhanh tác vụ phát triển và tệp tin giới thiệu, hướng dẫn thiết lập hệ thống.

### Thay đổi (Changed)
- Cập nhật kịch bản chạy đăng nhập trong `DrissionPageAutomationService.run_login` để nạp trình duyệt qua factory và bọc toàn bộ bằng khối lệnh `with` Context Manager giúp tài nguyên luôn được giải phóng an toàn khi có lỗi hoặc thoát.
- Loại bỏ hoàn toàn mã nguồn thừa và các import không sử dụng (Dict, List, ChromiumPage, ChromiumOptions) trong file `drission_page.py`.

---

## [1.0.0] - 2026-06-25

### Thêm mới (Added)
- Khởi tạo khung dự án tự động hóa mạng xã hội (Backend FastAPI).
- Thiết lập kịch bản đăng nhập cơ bản cho Facebook, YouTube, TikTok, Twitter sử dụng DrissionPage.
- Tích hợp kết nối cơ sở dữ liệu PostgreSQL qua SQLAlchemy để lưu trữ tài khoản và lịch sử đăng nhập.
- Cung cấp API endpoint stream logs trực quan qua kết nối SSE.
