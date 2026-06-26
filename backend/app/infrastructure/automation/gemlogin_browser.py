import re
import time
from pathlib import Path
from typing import Any

import requests
from DrissionPage import ChromiumPage, ChromiumOptions
from app.application.interfaces import BrowserContextManager


class GemLoginBrowser(BrowserContextManager):
    """
    Context manager to manage the GemLogin profile session and ChromiumPage lifecycle.
    """
    profile_key: str
    gemlogin_api_url: str
    gemlogin_profile_id: str | None
    gemlogin_profile_name: str | None
    page: ChromiumPage | None
    profile_id: str | None
    _logs: list[str]
    _log_index: int

    def __init__(
        self,
        profile_key: str,
        gemlogin_api_url: str,
        gemlogin_profile_id: str | None = None,
        gemlogin_profile_name: str | None = None
    ):
        self.profile_key = profile_key
        self.gemlogin_api_url = gemlogin_api_url
        self.gemlogin_profile_id = gemlogin_profile_id
        self.gemlogin_profile_name = gemlogin_profile_name
        self.page = None
        self.profile_id = None
        self._logs = []
        self._log_index = 0

    def log(self, msg: str) -> None:
        self._logs.append(msg)

    def get_new_logs(self) -> list[str]:
        new_logs = self._logs[self._log_index:]
        self._log_index = len(self._logs)
        return new_logs

    def __enter__(self) -> ChromiumPage:
        try:
            self.log("Đang khởi tạo trình duyệt qua GemLogin API...")

            # 1. Determine profile_id to use
            if self.gemlogin_profile_id:
                self.profile_id = self.gemlogin_profile_id
                self.log(f"Sử dụng GemLogin Profile ID cố định cấu hình từ .env: {self.profile_id}")
            else:
                self.profile_id = self._fetch_profile_id_by_name()

            # 2. Start the profile via API
            self.log(f"Đang mở trình duyệt cho profile ID: {self.profile_id}...")
            start_data = self._start_profile_api()

            # 3. Extract debugging port
            port = self._extract_port(start_data)
            if not port:
                self.log(f"Không thể tìm thấy cổng debugging từ phản hồi API: {start_data}")
                raise ValueError("Không tìm thấy cổng debugging.")

            # 4. Connect DrissionPage
            self.log(f"Đang kết nối DrissionPage tới cổng debug của trình duyệt: {port}...")
            co = ChromiumOptions()
            co.set_local_port(port)
            self.page = ChromiumPage(addr_or_opts=co)
            return self.page

        except Exception as e:
            self._cleanup()
            raise e

    def _fetch_profile_id_by_name(self) -> str:
        search_name = self.gemlogin_profile_name or "default"
        self.log(f"Đang kiểm tra danh sách profile trên GemLogin để tìm profile tên '{search_name}'...")
        try:
            res = requests.get(f"{self.gemlogin_api_url}/profiles", timeout=10)
            res.raise_for_status()
            profiles = res.json()
        except Exception as e_profiles:
            self.log(f"Không thể kết nối tới GemLogin API (Hãy đảm bảo ứng dụng GemLogin đang chạy trên cổng 1010): {str(e_profiles)}")
            raise e_profiles

        profiles_list = profiles.get("data", []) if isinstance(profiles, dict) else (profiles if isinstance(profiles, list) else [])

        for p in profiles_list:
            if isinstance(p, dict) and p.get("name") == search_name:
                p_id = p.get("id") or p.get("_id")
                if p_id:
                    self.log(f"Tìm thấy profile GemLogin '{search_name}' với ID: {p_id}")
                    return str(p_id)

        err_msg = f"Không tìm thấy profile '{search_name}' trên GemLogin và hệ thống đã cấu hình không tự động tạo mới."
        self.log(err_msg)
        raise ValueError(err_msg)

    def _start_profile_api(self) -> Any:
        try:
            res_start = requests.get(f"{self.gemlogin_api_url}/profiles/start/{self.profile_id}", timeout=20)
            res_start.raise_for_status()
            return res_start.json()
        except Exception as e_start:
            self.log(f"Lỗi khi gọi API mở profile: {str(e_start)}")
            raise e_start

    def _extract_port(self, data: Any) -> int | None:
        if not isinstance(data, dict):
            return None
        
        # Check direct or nested port
        if "port" in data:
            return int(data["port"])
        
        nested_data = data.get("data")
        if isinstance(nested_data, dict) and "port" in nested_data:
            return int(nested_data["port"])

        # Search in known URL keys
        keys = ["ws", "wsUrl", "selenium", "debuggerAddress", "browserWSEndpoint", "remote_debugging_address"]
        for key in keys:
            val = data.get(key) or (nested_data.get(key) if isinstance(nested_data, dict) else None)
            if isinstance(val, str):
                match = re.search(r':(\d+)', val)
                if match:
                    return int(match.group(1))
        return None

    def _take_screenshot(self) -> None:
        if not self.page:
            return
        try:
            backend_dir = Path(__file__).resolve().parents[3]
            screenshots_dir = backend_dir / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            screenshot_path = screenshots_dir / f"{self.profile_key}_{int(time.time())}.png"
            self.page.get_screenshot(path=str(screenshot_path), full_page=False)
            self.log(f"Đã chụp ảnh màn hình lưu tại: backend/screenshots/{screenshot_path.name}")
        except Exception as e_ss:
            self.log(f"Không thể chụp ảnh màn hình: {str(e_ss)}")

    def _close_profile_api(self) -> None:
        if not self.profile_id:
            return
        try:
            close_res = requests.get(f"{self.gemlogin_api_url}/profiles/close/{self.profile_id}", timeout=10)
            close_res.raise_for_status()
            self.log(f"Đã đóng profile GemLogin: {close_res.json()}")
        except Exception as e_close:
            self.log(f"Không thể gọi API đóng profile: {str(e_close)}")

    def _cleanup(self) -> None:
        if self.page:
            self._take_screenshot()
            self.log("Đang tắt trình duyệt...")
            try:
                # Let the browser window stay open for 3 seconds so user can see final state
                time.sleep(3)
                self._close_profile_api()
                try:
                    self.page.quit()
                except Exception:
                    pass
                self.log("Trình duyệt đã đóng.")
            except Exception as ex:
                self.log(f"Không thể đóng trình duyệt sạch sẽ: {str(ex)}")
        else:
            if self.profile_id:
                self.log("Trình duyệt chưa khởi tạo thành công, nhưng profile đã được mở. Đang đóng profile GemLogin...")
                self._close_profile_api()

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> bool:
        self._cleanup()
        return False
