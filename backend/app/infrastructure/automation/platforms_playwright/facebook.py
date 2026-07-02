import time
from typing import Generator, Dict, Any
from playwright.sync_api import Page
from app.domain.models import LoginStatus

def login_facebook(page: Page, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Đang truy cập trang chủ Facebook...")
    page.goto("https://www.facebook.com/")
    
    # Check if already logged in
    if page.locator("[role='feed']").count() > 0 or page.locator("[role='navigation']").count() > 0 or "facebook.com/home.php" in page.url:
        yield log_func("Đã phát hiện phiên đăng nhập sẵn có.")
        return LoginStatus.LOGGED_IN

    yield log_func("Nhập thông tin tài khoản Facebook...")
    email_input = page.locator("input[name='email']")
    pass_input = page.locator("input[name='pass']")
    
    if email_input.count() == 0 or pass_input.count() == 0:
        yield log_func("Không tìm thấy trường nhập liệu Facebook. Thử tìm locator khác...")
        email_input = page.locator("#email")
        pass_input = page.locator("#pass")

    if email_input.count() > 0 and pass_input.count() > 0:
        email_input.fill(username)
        time.sleep(0.5)
        pass_input.fill(password)
        time.sleep(0.5)
        
        login_btn = None
        for selector in ["button[name='login']", "[data-testid='royal_login_button']", "button[type='submit']", "input[type='submit']"]:
            btn = page.locator(selector)
            if btn.count() > 0:
                login_btn = btn
                break
                
        if login_btn:
            try:
                yield log_func("Click nút Đăng nhập...")
                login_btn.click()
            except Exception as e:
                yield log_func(f"Click thường thất bại ({str(e)}), gửi phím Enter trên ô mật khẩu...")
                pass_input.press("Enter")
        else:
            yield log_func("Không tìm thấy nút đăng nhập, gửi phím Enter trên ô mật khẩu...")
            pass_input.press("Enter")
            
        yield log_func("Chờ 10 giây để người dùng giải CAPTCHA (nếu có)...")
        time.sleep(10)
            
        yield log_func("Đang đợi Facebook xác thực (chờ động tối đa 10 giây)...")
        
        # Dynamic polling
        final_status = LoginStatus.LOGGED_OUT
        for _ in range(20): # 20 * 0.5s = 10s
            time.sleep(0.5)
            url = page.url
            if "checkpoint" in url:
                yield log_func("Tài khoản yêu cầu phê duyệt đăng nhập / 2FA.")
                final_status = LoginStatus.CHECKPOINT
                break
            elif "login" in url or "error" in url or page.locator(".login_error_box").count() > 0 or page.locator("#error_box").count() > 0:
                yield log_func("Đăng nhập thất bại. Sai tài khoản mật khẩu hoặc bị chặn.")
                final_status = LoginStatus.LOGGED_OUT
                break
            elif page.locator("[role='feed']").count() > 0 or page.locator("[role='navigation']").count() > 0 or "home" in url or "feed" in url or "facebook.com/home.php" in url:
                yield log_func("Đăng nhập thành công vào trang chủ.")
                final_status = LoginStatus.LOGGED_IN
                break
            elif "disabled" in url or "suspended" in url or "locked" in page.content().lower():
                yield log_func("Tài khoản Facebook đã bị vô hiệu hóa.")
                final_status = LoginStatus.DEAD
                break
        else:
            # Check final states after timeout
            url = page.url
            yield log_func(f"Hết thời gian chờ động. URL hiện tại: {url}")
            if "checkpoint" in url:
                final_status = LoginStatus.CHECKPOINT
            elif page.locator("[role='feed']").count() > 0 or page.locator("[role='navigation']").count() > 0 or "home" in url or "feed" in url or "facebook.com/home.php" in url:
                final_status = LoginStatus.LOGGED_IN
            elif "disabled" in url or "suspended" in url or "locked" in page.content().lower():
                final_status = LoginStatus.DEAD
            else:
                final_status = LoginStatus.LOGGED_OUT
                yield log_func("Không rõ trạng thái cụ thể, mặc định chưa đăng nhập.")
                
        return final_status
    else:
        yield log_func("Không thể định vị được ô nhập tài khoản/mật khẩu.")
        return LoginStatus.LOGGED_OUT
