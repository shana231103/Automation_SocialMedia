# Project Rules

- Lập kế hoạch triển khai (planning) cho mỗi Phase mới phải được lưu trữ trực tiếp vào thư mục `docs/plans/` của dự án dưới dạng Markdown (ví dụ: `docs/plans/016_smart_local_content_cache.md`), không tự ý tạo các tệp thiết kế chi tiết (detail/design/blueprint) trừ khi được yêu cầu cụ thể.

## Quy tắc quản lý tệp tin thử nghiệm (Scratch & Demo Files)
- **Vị trí lưu trữ:** Mọi tệp demo, script chạy thử nghiệm, script kiểm tra tạm thời hoặc các tệp nháp (scratch files) bắt buộc phải được tạo trong thư mục scratch/.
- **Cấm tạo ở gốc:** Tuyệt đối không tạo trực tiếp các tệp tin thử nghiệm này tại thư mục gốc (root) của dự án để giữ cho cấu trúc thư mục dự án luôn sạch sẽ.

## Quy tắc quản lý tiến trình phát triển và Planning Prompts
- **Không ghi đè Phase cũ:** Khi có yêu cầu hoặc ý tưởng mới cho một tính năng đã được triển khai trước đó, tuyệt đối không được sửa đổi hay ghi đè các tệp tin prompt cũ của Phase đó trong thư mục `docs/plans/prompts/`.
- **Tạo Phase mở rộng:** 
  - Nếu là tính năng bổ sung/mở rộng trực tiếp từ Phase cũ, bắt buộc phải tạo một Phase phụ mới có gắn hậu tố chữ cái (ví dụ: Phase `17` đã thực thi xong thì tạo tệp prompt mới cho Phase `17b` làm `017b_*.md`).
  - Nếu là một tính năng hoàn toàn mới hoặc khác biệt về mặt chức năng, phải nâng số thứ tự Phase (ví dụ: Phase `18` với tên tệp dạng `018_*.md`).
