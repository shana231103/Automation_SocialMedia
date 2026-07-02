import re
import time
import subprocess
import requests
from pathlib import Path
from typing import Any
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Playwright
from app.application.interfaces import BrowserContextManager

class GemLoginPlaywrightBrowser(BrowserContextManager):
    """
    Context manager to manage the GemLogin profile session and Playwright Page lifecycle.
    """
    profile_key: str
    gemlogin_api_url: str
    gemlogin_profile_id: str | None
    gemlogin_profile_name: str | None
    
    playwright: Playwright | None
    browser: Browser | None
    context: BrowserContext | None
    page: Page | None
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
        self.playwright = None
        self.browser = None
        self.context = None
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

    def __enter__(self) -> Page:
        try:
            self.log("Đang khởi tạo trình duyệt qua GemLogin API (Playwright)...")

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

            # 4. Connect Playwright via CDP
            self.log(f"Đang kết nối Playwright tới cổng debug của trình duyệt: {port}...")
            import sys
            import asyncio
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            self.playwright = sync_playwright().start()
            
            # Retry connection up to 5 times with a 1s delay
            for attempt in range(5):
                try:
                    self.browser = self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                    break
                except Exception as e_conn:
                    if attempt == 4:
                        raise e_conn
                    self.log(f"Chờ trình duyệt sẵn sàng (lần thử {attempt + 1}/5)...")
                    time.sleep(1)
                    
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
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
            self.page.screenshot(path=str(screenshot_path), full_page=False)
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
                if self.browser:
                    self.browser.close()
                if self.playwright:
                    self.playwright.stop()
                self._close_profile_api()
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


class LocalPlaywrightBrowser(BrowserContextManager):
    """
    Context manager to launch Google Chrome locally via Command Line,
    connect Playwright via CDP, and manage its lifecycle.
    """
    profile_key: str
    chrome_path: str
    port: int
    user_data_dir: Path
    
    playwright: Playwright | None
    browser: Browser | None
    context: BrowserContext | None
    page: Page | None
    process: subprocess.Popen | None
    _logs: list[str]
    _log_index: int

    def __init__(
        self,
        profile_key: str,
        chrome_path: str = r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        port: int = 9222,
        user_data_dir: str | None = None
    ):
        self.profile_key = profile_key
        self.chrome_path = chrome_path
        self.port = port
        
        # Determine user data dir
        backend_dir = Path(__file__).resolve().parents[3]
        if user_data_dir:
            self.user_data_dir = Path(user_data_dir)
        else:
            self.user_data_dir = backend_dir / "profiles" / f"local_{profile_key}"
            
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.process = None
        self._logs = []
        self._log_index = 0

    def log(self, msg: str) -> None:
        self._logs.append(msg)

    def get_new_logs(self) -> list[str]:
        new_logs = self._logs[self._log_index:]
        self._log_index = len(self._logs)
        return new_logs

    def __enter__(self) -> Page:
        try:
            self.log(f"Đang chuẩn bị thư mục cấu hình trình duyệt tại: {self.user_data_dir}")
            self.user_data_dir.mkdir(parents=True, exist_ok=True)

            self.log(f"Khởi chạy trình duyệt bằng dòng lệnh: {self.chrome_path} trên cổng debug {self.port}...")
            # Command arguments
            args = [
                self.chrome_path,
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir={self.user_data_dir}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            # Spawn the browser process
            self.process = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for browser to initialize
            time.sleep(2)

            self.log(f"Kết nối Playwright tới cổng debug: {self.port}...")
            import sys
            import asyncio
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            self.playwright = sync_playwright().start()
            
            # Retry connection up to 5 times with a 1s delay
            for attempt in range(5):
                try:
                    self.browser = self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}")
                    break
                except Exception as e_conn:
                    if attempt == 4:
                        raise e_conn
                    self.log(f"Chờ trình duyệt local sẵn sàng (lần thử {attempt + 1}/5)...")
                    time.sleep(1)
                    
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            return self.page

        except Exception as e:
            self._cleanup()
            raise e

    def _cleanup(self) -> None:
        # 1. Take screenshot
        if self.page:
            try:
                backend_dir = Path(__file__).resolve().parents[3]
                screenshots_dir = backend_dir / "screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                
                screenshot_path = screenshots_dir / f"{self.profile_key}_{int(time.time())}.png"
                self.page.screenshot(path=str(screenshot_path), full_page=False)
                self.log(f"Đã chụp ảnh màn hình lưu tại: backend/screenshots/{screenshot_path.name}")
            except Exception as e_ss:
                self.log(f"Không thể chụp ảnh màn hình: {str(e_ss)}")

            # 2. Close Playwright browser connection
            self.log("Đang đóng kết nối Playwright...")
            try:
                if self.browser:
                    self.browser.close()
                if self.playwright:
                    self.playwright.stop()
            except Exception:
                pass

        # 3. Kill Chrome process
        if self.process:
            self.log("Đang đóng tiến trình Chrome chạy dòng lệnh...")
            try:
                self.process.terminate()
                # Wait for up to 5 seconds for the process to exit
                self.process.wait(timeout=5)
                self.log("Tiến trình Chrome đã đóng.")
            except subprocess.TimeoutExpired:
                self.log("Chrome không phản hồi tắt. Tiến hành ép buộc dừng tiến trình (kill)...")
                self.process.kill()
                self.process.wait()
                self.log("Đã dừng tiến trình Chrome bằng lệnh ép buộc.")
            except Exception as e:
                self.log(f"Lỗi khi đóng tiến trình: {str(e)}")

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> bool:
        self._cleanup()
        return False
