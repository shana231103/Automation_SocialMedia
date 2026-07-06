# Phase 003: Tái cấu trúc loại bỏ mã trùng lặp giữa hai Dịch vụ Tự động hóa

## 1. Vấn đề hiện tại
*   `DrissionPageAutomationService` và `PlaywrightAutomationService` có cấu trúc mã xử lý `run_action` trùng lặp đến 90%.
*   Cả hai đều thực hiện các bước: khởi tạo log, lấy lớp Action, quản lý trình duyệt thông qua khối lệnh context manager (`with`), bắt lỗi (`except`), chụp ảnh màn hình hoặc ghi nhận lỗi, giải phóng tài nguyên trong khối lệnh `finally` và yield các kết quả SSE.
*   Việc này làm tăng chi phí bảo trì và dễ sinh lỗi khi sửa đổi luồng ghi log hoặc dọn dẹp trình duyệt chung.

## 2. Giải pháp kiến trúc
1.  Định nghĩa một lớp cơ sở chung `BaseAutomationService` kế thừa từ giao diện `AutomationService`.
2.  Lớp cơ sở này sẽ đóng vai trò là "Template Method Pattern" (hoặc Runner) định nghĩa chính xác luồng thực hiện chạy tác vụ tự động hóa, bọc bắt lỗi và gom log.
3.  Lớp cơ sở nhận vào:
    *   `browser_manager_factory`: Hàm tạo trình duyệt tương ứng.
    *   `page_wrapper_class`: Lớp wrapper tương ứng (`DrissionPageWrapper` hoặc `PlaywrightPageWrapper`).
4.  Cả hai dịch vụ cụ thể chỉ cần gọi hàm khởi tạo `super().__init__` truyền các tham số trên và không chứa logic trùng lặp nào khác.

## 3. Các thay đổi dự kiến
*   **Thêm mới** [base_service.py](file:///c:/Users/LAPTOP/OneDrive/Ta%CC%80i%20li%C3%AA%CC%A3u/GitHub/Automation_SocialMedia/backend/app/infrastructure/automation/base_service.py): Chứa lớp `BaseAutomationService`.
*   **Cập nhật** [drission_page.py](file:///c:/Users/LAPTOP/OneDrive/Ta%CC%80i%20li%C3%AA%CC%A3u/GitHub/Automation_SocialMedia/backend/app/infrastructure/automation/drission_page.py): Kế thừa `BaseAutomationService`.
*   **Cập nhật** [playwright_service.py](file:///c:/Users/LAPTOP/OneDrive/Ta%CC%80i%20li%C3%AA%CC%A3u/GitHub/Automation_SocialMedia/backend/app/infrastructure/automation/playwright_service.py): Kế thừa `BaseAutomationService`.

## 4. Kế hoạch kiểm thử
*   Chạy unit test: `python -m unittest tests/unit/automation/test_action_registry.py` để đảm bảo cơ chế dispatch action vẫn hoạt động bình thường.
*   Chạy test tích hợp: `python test_automation.py` để kiểm tra luồng login thực tế.
