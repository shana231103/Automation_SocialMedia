import subprocess
import time
from pathlib import Path
from typing import Any
from DrissionPage import ChromiumPage, ChromiumOptions
from app.application.interfaces import BrowserContextManager

class LocalBrowser(BrowserContextManager):
    """
    Context manager to launch Google Chrome locally via Command Line,
    connect DrissionPage, and manage its lifecycle.
    """
    profile_key: str
    chrome_path: str
    port: int
    user_data_dir: Path
    page: ChromiumPage | None
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

    def __enter__(self) -> ChromiumPage:
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

            self.log(f"Kết nối DrissionPage tới cổng debug: {self.port}...")
            co = ChromiumOptions()
            co.set_local_port(self.port)
            self.page = ChromiumPage(addr_or_opts=co)
            return self.page

        except Exception as e:
            self._cleanup()
            raise e

    def _cleanup(self) -> None:
        # 1. Chụp ảnh màn hình
        if self.page:
            try:
                backend_dir = Path(__file__).resolve().parents[3]
                screenshots_dir = backend_dir / "screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                
                screenshot_path = screenshots_dir / f"{self.profile_key}_{int(time.time())}.png"
                self.page.get_screenshot(path=str(screenshot_path), full_page=False)
                self.log(f"Đã chụp ảnh màn hình lưu tại: backend/screenshots/{screenshot_path.name}")
            except Exception as e_ss:
                self.log(f"Không thể chụp ảnh màn hình: {str(e_ss)}")

            # 2. Đóng trình duyệt sạch sẽ qua DrissionPage
            self.log("Đang đóng kết nối DrissionPage...")
            try:
                self.page.quit()
            except Exception:
                pass

        # 3. Kết liễu tiến trình Chrome qua Command Line
        if self.process:
            self.log("Đang đóng tiến trình Chrome chạy dòng lệnh...")
            try:
                self.process.terminate()
                # Chờ tối đa 5 giây cho tiến trình tắt
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
