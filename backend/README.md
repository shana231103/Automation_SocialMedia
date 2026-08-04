# Automation Social Media — Backend

Backend FastAPI dùng để quản lý tài khoản và kiểm tra trạng thái đăng nhập Facebook, YouTube, TikTok và X (Twitter) qua trình duyệt GemLogin. Hệ thống hỗ trợ DrissionPage hoặc Playwright, stream tiến trình bằng Server-Sent Events (SSE), chạy nhiều tài khoản theo batch và lưu lịch sử vào PostgreSQL.

## Tính năng chính

- CRUD tài khoản mạng xã hội và gán `gemlogin_profile_name` riêng cho từng tài khoản.
- Đăng nhập đơn hoặc batch, giới hạn số phiên chạy đồng thời và stream log thời gian thực bằng SSE.
- Kiến trúc driver-agnostic: cùng một platform flow hoạt động với DrissionPage và Playwright.
- AI selector fallback qua Ollama local (`qwen3.5:9b`) khi selector tĩnh của ô đăng nhập không còn phù hợp.
- AI status verification ghi rõ dự đoán, độ tin cậy, lý do, bằng chứng hình ảnh/DOM và mã lỗi fallback.
- Phân loại trạng thái `logged in`, `logged out`, `checkpoint` và `dead` bằng hostname/path cùng tín hiệu UI cụ thể.
- Cooperative cancellation: phiên đang chờ có thể dừng sớm khi client đóng kết nối batch.
- Unit test không yêu cầu PostgreSQL hoặc GemLogin thật.

> AI chỉ hỗ trợ tìm selector và đánh giá trạng thái. Hệ thống không tự giải CAPTCHA, 2FA hoặc bước xác minh bảo mật; người dùng vẫn phải xử lý thủ công.

## Công nghệ

- Python 3.11+
- FastAPI và Uvicorn
- SQLAlchemy 2, PostgreSQL và psycopg 3
- DrissionPage hoặc Playwright
- Vue 3 frontend
- Ollama local với model vision `qwen3.5:9b`

## Cấu trúc chính

```text
backend/
├── app/
│   ├── application/
│   │   ├── interfaces.py
│   │   └── use_cases/
│   ├── domain/
│   ├── infrastructure/
│   │   ├── ai/                    # DOM parser và AI selector fallback
│   │   ├── automation/
│   │   │   ├── actions/           # Action registry và LoginAction
│   │   │   ├── adapters/          # Adapter DrissionPage/Playwright
│   │   │   ├── platforms/         # Facebook, TikTok, X và YouTube
│   │   │   ├── base_service.py
│   │   │   └── *_browser.py
│   │   └── database/
│   ├── presentation/              # FastAPI routes và Pydantic schemas
│   └── main.py
├── tests/unit/
├── requirements.txt
├── create_db.py
└── test_automation.py
```

## Cài đặt trên Windows PowerShell

Từ thư mục `backend`:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn script kích hoạt, có thể bỏ qua bước activate và gọi trực tiếp `.venv\Scripts\python.exe` trong các lệnh bên dưới.

## Cấu hình

Tạo `backend/.env` và không commit file này:

```env
AUTOMATION_PROVIDER=drissionpage

DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/social_automation

GEMLOGIN_API_URL=http://127.0.0.1:1010/api
GEMLOGIN_PROFILE_NAME=default

MAX_CONCURRENT_LOGINS=3
MAX_BATCH_SIZE=100

ENABLE_AI_FALLBACK=true
ENABLE_AI_STATUS_VERIFICATION=true
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_TIMEOUT_SECONDS=60
OLLAMA_SELECTOR_TIMEOUT_SECONDS=20
```

Giá trị `AUTOMATION_PROVIDER` hợp lệ là `drissionpage` hoặc `playwright`. Ollama phải chạy cục bộ tại `OLLAMA_BASE_URL` và đã tải model `OLLAMA_MODEL`. Không cấu hình API key hoặc endpoint AI bên ngoài.

## Khởi tạo database

```powershell
python create_db.py
```

## Chạy backend

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

Dùng `python -m uvicorn` thay vì gọi `uvicorn` trực tiếp để bảo đảm server chạy bằng đúng Python trong virtual environment.

- API: `http://127.0.0.1:8000/api`
- Swagger UI: `http://127.0.0.1:8000/docs`

## API chính

| Method | Endpoint | Chức năng |
|---|---|---|
| `GET` | `/api/accounts` | Danh sách tài khoản |
| `POST` | `/api/accounts` | Tạo tài khoản |
| `DELETE` | `/api/accounts/{account_id}` | Xóa tài khoản |
| `GET` | `/api/history` | Lịch sử đăng nhập |
| `POST` | `/api/history/clear` | Xóa lịch sử |
| `GET` | `/api/run-login/{account_id}` | Chạy một tài khoản và stream SSE |
| `GET` | `/api/batch-login?account_ids=1,2,3` | Chạy batch và stream SSE |
| `GET` | `/api/ai/status` | Trạng thái AI selector fallback |

API hiện không có cơ chế xác thực. Chỉ nên chạy trong máy cá nhân hoặc mạng nội bộ được bảo vệ.

## Kiểm thử

Chạy toàn bộ unit test từ thư mục `backend`:

```powershell
python -m unittest discover -s tests -v
```

Chạy integration test với database và trình duyệt thật:

```powershell
python test_automation.py
```

Integration test yêu cầu PostgreSQL, GemLogin và cấu hình `.env` hợp lệ.

## Quy tắc xác định trạng thái

- `logged in`: hostname/path hợp lệ và/hoặc có UI xác nhận phiên đăng nhập.
- `checkpoint`: CAPTCHA, 2FA hoặc security challenge cần người dùng xử lý.
- `dead`: chỉ khi có bằng chứng cụ thể rằng tài khoản bị disabled, suspended hoặc banned.
- `logged out`: sai thông tin đăng nhập, không tìm thấy tài khoản hoặc hết thời gian mà không có trạng thái xác định.

Không dùng substring chung như `home`, `youtube.com`, `foryou` hoặc `locked` trên toàn bộ URL/HTML để kết luận trạng thái.
