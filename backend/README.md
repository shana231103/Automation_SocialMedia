# Automation Social Media — Backend

FastAPI backend quản lý tài khoản và tự động kiểm tra đăng nhập Facebook, YouTube, TikTok và X qua GemLogin. Hệ thống hỗ trợ DrissionPage hoặc Playwright, SSE cho đăng nhập đơn/batch, và AI từ xa qua Gemini hoặc OpenAI theo cơ chế opt-in.

## Cài đặt

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

Sao chép `backend/.env.example` thành `backend/.env`, điền cấu hình database/GemLogin, rồi chạy:

```powershell
python create_db.py
python -m uvicorn app.main:app --reload --port 8000
```

Swagger UI nằm tại `http://127.0.0.1:8000/docs`. API không có lớp xác thực riêng, vì vậy chỉ nên chạy trên máy cá nhân hoặc mạng nội bộ được bảo vệ.

## AI đa nhà cung cấp

AI mặc định tắt (`AI_ENABLED=false`), nên cấu hình mặc định không phát sinh request, chi phí hay phụ thuộc vào dịch vụ bên ngoài. Khi bật, chọn đúng một `AI_PROVIDER=gemini|openai`; hệ thống chỉ đọc API key của provider đã chọn và không tự động chuyển sang provider khác khi lỗi.

- `semantic`: Gemini hoặc OpenAI hỗ trợ tìm selector và đánh giá trạng thái cuối. AI lỗi hoặc cấu hình sai sẽ suy giảm an toàn về selector/status xác định sẵn.
- `/api/ai/status`: trả về health/capability trung lập, không gọi model và không lộ secret.

Ảnh chụp đã che trường nhạy cảm, URL đã loại credential/query/fragment và DOM không chứa giá trị form mới được gửi tới provider. Username/password không được đưa vào prompt hoặc lịch sử model. Dữ liệu vẫn được xử lý từ xa theo điều khoản của provider và có thể phát sinh chi phí token; hãy dùng key giới hạn quyền và ngân sách.

Gemini và OpenAI chỉ đưa ra kết quả có cấu trúc cho selector và trạng thái cuối; provider không điều khiển trình duyệt. CAPTCHA, MFA và security challenge được phân loại theo chính sách xác định sẵn, không được tự động giải hoặc nhập mã xác minh.

## Chuyển từ Ollama

Các biến `OLLAMA_*`, `ENABLE_AI_FALLBACK` và `ENABLE_AI_STATUS_VERIFICATION` không còn kích hoạt AI. Thay bằng `AI_ENABLED`, `AI_PROVIDER`, `AI_LOGIN_STRATEGY`, model và API key tương ứng trong `.env.example`. Runtime không còn phụ thuộc `browser-use` hoặc Ollama.

## API chính

| Method | Endpoint | Chức năng |
|---|---|---|
| `GET/POST` | `/api/accounts` | Liệt kê/tạo tài khoản |
| `DELETE` | `/api/accounts/{account_id}` | Xóa tài khoản |
| `GET` | `/api/history` | Lịch sử đăng nhập |
| `GET` | `/api/run-login/{account_id}` | Đăng nhập đơn qua SSE |
| `GET` | `/api/batch-login?account_ids=1,2` | Đăng nhập batch qua SSE |
| `GET` | `/api/ai/status` | Trạng thái AI trung lập |

SSE hiện hữu giữ nguyên các event đăng nhập và batch. Mỗi tài khoản vẫn phát đúng một kết quả cuối.

## Kiểm thử

Các unit test dùng fake transport, không cần mạng hoặc credential thật:

```powershell
python -m unittest discover -s tests -v
```

Smoke test từ xa chỉ được chạy thủ công sau khi đặt credential và `RUN_REMOTE_AI_SMOKE_TESTS=true`; không bật cờ này trong CI mặc định. Integration test trình duyệt/database dùng `python test_automation.py` và yêu cầu PostgreSQL cùng GemLogin thật.
