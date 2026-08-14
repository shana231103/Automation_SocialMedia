# GemLogin Integration Knowledge

## Mục đích

Tài liệu độc lập này cung cấp ngữ cảnh kỹ thuật cần thiết để AI hoặc lập trình viên tích hợp GemLogin làm trình duyệt antidetect trong một dự án khác. Nội dung được trích xuất từ Project Memory, tài liệu kiến trúc và implementation hiện hành của dự án Automation Social Media.

## 1. Tổng quan tích hợp

GemLogin desktop cung cấp REST API cục bộ để:

1. Liệt kê các browser profile.
2. Mở một profile và nhận cổng remote debugging/CDP.
3. Cho Playwright hoặc DrissionPage kết nối vào Chromium của profile.
4. Đóng profile sau khi automation kết thúc hoặc gặp lỗi.

Luồng tổng quát:

```text
GemLogin desktop đang chạy
        |
        v
Xác định profile ID hoặc tìm ID theo tên
        |
        v
GET /profiles/start/{profile_id}
        |
        v
Trích xuất remote-debugging port
        |
        v
Kết nối Playwright hoặc DrissionPage qua CDP
        |
        v
Thực hiện automation
        |
        v
Đóng driver và GET /profiles/close/{profile_id}
```

## 2. Cấu hình môi trường

```env
# Base URL đã bao gồm /api.
GEMLOGIN_API_URL=http://127.0.0.1:1010/api

# Ưu tiên dùng ID nếu biết trước.
GEMLOGIN_PROFILE_ID=

# Nếu không có ID, tìm profile theo tên.
GEMLOGIN_PROFILE_NAME=default

# Adapter automation của ứng dụng.
AUTOMATION_PROVIDER=playwright
# Hoặc: drissionpage
```

Thứ tự chọn profile:

1. `GEMLOGIN_PROFILE_ID` nếu được cấu hình.
2. Tên profile được truyền vào tại thời điểm chạy.
3. `GEMLOGIN_PROFILE_NAME`.
4. Tên mặc định `default`.

Implementation hiện tại không tự động tạo profile khi không tìm thấy. Profile phải tồn tại sẵn trong GemLogin.

## 3. Hợp đồng REST API đang được implementation sử dụng

`base_url` mặc định là `http://127.0.0.1:1010/api`.

| Mục đích | Request | Timeout | Kết quả mong đợi |
|---|---|---:|---|
| Liệt kê profile | `GET {base_url}/profiles` | 10 giây | Danh sách trực tiếp hoặc `{ "data": [...] }` |
| Mở profile | `GET {base_url}/profiles/start/{profile_id}` | 20 giây | JSON chứa port hoặc địa chỉ CDP/WebSocket |
| Đóng profile | `GET {base_url}/profiles/close/{profile_id}` | 10 giây | JSON xác nhận |

### Tìm profile theo tên

API danh sách profile có thể trả về một mảng trực tiếp hoặc object có trường `data`:

```json
{
  "data": [
    {
      "id": "profile-id",
      "name": "default"
    }
  ]
}
```

Quy tắc xử lý:

- Đối chiếu chính xác trường `name`.
- Profile ID có thể nằm trong `id` hoặc `_id`.
- Nếu không tìm thấy profile, dừng với lỗi rõ ràng; không tự tạo profile ngoài ý muốn.

### Trích xuất cổng debug

Cổng có thể xuất hiện tại:

- `port` ở cấp ngoài cùng.
- `data.port`.
- Một URL hoặc địa chỉ trong các trường:
  - `ws`
  - `wsUrl`
  - `selenium`
  - `debuggerAddress`
  - `browserWSEndpoint`
  - `remote_debugging_address`

Implementation hiện tại tìm mẫu `:<port>` trong các giá trị chuỗi nói trên.

## 4. Kết nối bằng Playwright

Phụ thuộc Python:

- `requests`
- `playwright`
- `python-dotenv` nếu đọc cấu hình từ `.env`

Sau khi mở profile và lấy được `port`:

```python
from playwright.sync_api import sync_playwright

playwright = sync_playwright().start()
browser = playwright.chromium.connect_over_cdp(
    f"http://127.0.0.1:{port}"
)

context = browser.contexts[0]
page = context.pages[0] if context.pages else context.new_page()
```

Khuyến nghị vận hành:

- Thử kết nối tối đa 5 lần.
- Chờ 1 giây giữa các lần thử để Chromium có thời gian mở CDP listener.
- Trên Windows, adapter hiện tại thiết lập `WindowsProactorEventLoopPolicy` trước khi khởi tạo Playwright.
- Playwright đồng bộ nên chạy trong worker thread nếu ứng dụng chính sử dụng event loop async.

## 5. Kết nối bằng DrissionPage

Phụ thuộc Python:

- `requests`
- `DrissionPage`
- `python-dotenv` nếu đọc cấu hình từ `.env`

Sau khi mở profile và lấy được `port`:

```python
from DrissionPage import ChromiumOptions, ChromiumPage

options = ChromiumOptions()
options.set_local_port(port)
page = ChromiumPage(addr_or_opts=options)
```

DrissionPage là synchronous. Khi tích hợp với FastAPI hoặc một event loop async, nên chạy automation trong thread executor để không chặn event loop chính.

## 6. Mẫu kiến trúc được khuyến nghị

Ẩn GemLogin sau một abstraction quản lý browser context:

```python
from abc import ABC, abstractmethod
from typing import Any


class BrowserContextManager(ABC):
    @abstractmethod
    def get_new_logs(self) -> list[str]:
        pass

    @abstractmethod
    def __enter__(self) -> Any:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        pass
```

Cách sử dụng:

```python
browser_manager = browser_manager_factory(profile_key, profile_name)

with browser_manager as page:
    # Logic automation chỉ phụ thuộc page abstraction.
    # Việc mở và đóng GemLogin thuộc trách nhiệm browser manager.
    ...
```

Lợi ích:

- Tách nghiệp vụ automation khỏi GemLogin REST API.
- Có thể thay Playwright bằng DrissionPage mà không sửa luồng nghiệp vụ.
- Có thể thêm GoLogin hoặc browser local bằng cách cung cấp factory khác.
- `__exit__` vẫn chạy khi code bên trong khối `with` phát sinh exception.

## 7. Quản lý vòng đời và cleanup

Adapter cần bảo đảm:

1. Nếu API đã mở profile nhưng kết nối driver thất bại, vẫn gọi API đóng profile.
2. Khi thoát context, đóng kết nối driver và profile GemLogin.
3. Không dùng lệnh kill Chrome diện rộng vì có thể ảnh hưởng browser cá nhân của người dùng.
4. Không bỏ qua lỗi cleanup; ít nhất phải ghi log để chẩn đoán profile hoặc port bị kẹt.
5. Một profile/cổng debug chỉ nên có một automation session kết nối tại một thời điểm.

Thứ tự cleanup tham khảo cho Playwright:

```text
Đóng Browser/CDP connection
        -> dừng Playwright
        -> gọi /profiles/close/{profile_id}
```

Thứ tự cleanup tham khảo cho DrissionPage:

```text
Gọi /profiles/close/{profile_id}
        -> page.quit()
```

Nếu dự án cần ảnh chẩn đoán, có thể chụp screenshot trước khi đóng page. Không nên chụp hoặc gửi dữ liệu chứa credential mà chưa che các input nhạy cảm.

## 8. Chạy đồng thời

- Không cho nhiều worker dùng cùng profile hoặc cùng debug port.
- Mỗi worker nên được cấp một profile riêng hoặc một slot profile riêng.
- Database session và browser context của từng worker phải độc lập.
- Khi người dùng hủy tác vụ, truyền cancellation signal xuống luồng automation và vẫn thực hiện cleanup.
- CAPTCHA, MFA và security challenge là ranh giới thao tác thủ công; không cố bypass bằng automation hoặc AI.

## 9. Xử lý lỗi tối thiểu

Phân biệt các nhóm lỗi sau:

- Không kết nối được GemLogin API: GemLogin desktop chưa chạy, base URL sai hoặc port controller bị chiếm.
- Không tìm thấy profile: tên không khớp hoặc ID không tồn tại.
- Start profile thành công nhưng không có port: response schema khác dự kiến.
- Có port nhưng CDP chưa sẵn sàng: thực hiện retry có giới hạn.
- Driver lỗi trong khi chạy: đóng profile trong `finally` hoặc `__exit__`.
- Đóng profile thất bại: ghi log đầy đủ và không chuyển sang kill Chrome diện rộng.

Không hardcode controller port trong logic nghiệp vụ. Luôn cho phép cấu hình bằng `GEMLOGIN_API_URL` và kiểm tra API có thể truy cập trước khi bắt đầu automation dài.

## 10. Điểm không nhất quán trong nguồn kiến thức

Một số tài liệu Project Memory mô tả API dưới dạng:

```text
POST /api/profiles/start
POST /api/profiles/stop
```

Trong khi hai adapter hiện hành thực tế gọi:

```text
GET /api/profiles/start/{profile_id}
GET /api/profiles/close/{profile_id}
```

Khi chuyển kiến thức sang dự án khác:

1. Dùng implementation hiện hành làm hợp đồng tham chiếu ban đầu.
2. Xác minh endpoint với phiên bản GemLogin đang cài trên máy đích.
3. Cô lập các endpoint trong một client/adapter để dễ thay đổi nếu GemLogin đổi API.
4. Không rải trực tiếp URL endpoint trong service nghiệp vụ.

## 11. Checklist chuyển sang dự án khác

- [ ] Cài và chạy GemLogin desktop trên máy thực thi automation.
- [ ] Xác nhận `GEMLOGIN_API_URL` truy cập được.
- [ ] Tạo sẵn profile trong GemLogin.
- [ ] Chọn profile bằng ID hoặc tên.
- [ ] Gọi API start và kiểm tra response thực tế.
- [ ] Trích xuất debug port/CDP endpoint.
- [ ] Kết nối Playwright hoặc DrissionPage.
- [ ] Đặt retry có giới hạn cho giai đoạn CDP khởi động.
- [ ] Không dùng chung profile/port giữa các worker đồng thời.
- [ ] Dùng context manager hoặc `try/finally` để cleanup.
- [ ] Gọi API close kể cả khi driver khởi tạo thất bại.
- [ ] Che credential trong screenshot, DOM và log.
- [ ] Kiểm thử riêng start, attach, automation exception và cleanup.

## 12. Nguồn nội bộ đã trích xuất

### Project Memory

- `.agents/memory/project-summary.md`
- `.agents/memory/architecture/browser.md`
- `.agents/memory/modules/backend_infrastructure.md`
- `.agents/memory/modules/backend_application.md`
- `.agents/memory/services/automation_service.md`
- `.agents/memory/lessons/implementation-pitfalls.md`
- `.agents/memory/lessons/known-problems.md`
- `.agents/memory/lessons/architectural-decisions.md`
- `.agents/memory/rag/keyword-index.md`
- `.agents/memory/indexes/file-map.json`

### Tài liệu và implementation

- `backend/docs/browser_refactor_training.md`
- `backend/app/infrastructure/automation/gemlogin_browser.py`
- `backend/app/infrastructure/automation/playwright_browser.py`
- `backend/app/infrastructure/automation/drission_page.py`
- `backend/app/infrastructure/automation/playwright_service.py`

Project Memory được dùng để trích xuất tài liệu này có `last_updated_at` là `2026-08-13T21:54:45.3126105+07:00`. Chi tiết endpoint được đối chiếu thêm với implementation hiện hành do Memory chưa phản ánh nhất quán hợp đồng API.
