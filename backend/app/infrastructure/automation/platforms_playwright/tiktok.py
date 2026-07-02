import time
from typing import Generator, Dict, Any
from playwright.sync_api import Page
from app.domain.models import LoginStatus

def login_tiktok(page: Page, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Đang truy cập trang đăng nhập TikTok...")
    page.goto("https://www.tiktok.com/login/phone-or-email/email")
    
    # Check if already logged in
    if "tiktok.com" in page.url and (page.locator("[data-e2e='profile-icon']").count() > 0 or page.locator("[data-e2e='profile-avatar']").count() > 0):
        yield log_func("Đã phát hiện phiên đăng nhập TikTok sẵn có.")
        return LoginStatus.LOGGED_IN
        
    yield log_func("Đang nhập tài khoản email/username TikTok...")
    user_input = page.locator("input[name='username']")
    pass_input = page.locator("input[type='password']")
    
    if user_input.count() > 0 and pass_input.count() > 0:
        user_input.fill(username)
        time.sleep(0.5)
        pass_input.fill(password)
        time.sleep(0.5)
        
        yield log_func("Click đăng nhập...")
        submit_btn = page.locator("button[type='submit']")
        if submit_btn.count() > 0:
            submit_btn.click()
        else:
            pass_input.press("Enter")
            
        yield log_func("Đang chờ TikTok xử lý và hiển thị CAPTCHA nếu có (chờ động)...")
        
        # Polling for captcha or login success for up to 8s
        captcha_detected = False
        for _ in range(16): # 16 * 0.5s = 8s
            time.sleep(0.5)
            # Check if captcha is visible
            if page.locator("[id='captcha-wrapper']").count() > 0 or page.locator(".captcha-slider").count() > 0 or page.locator(".captcha_verify_container").count() > 0:
                captcha_detected = True
                break
            # Check if logged in early
            if page.locator("[data-e2e='profile-icon']").count() > 0 or page.locator("[data-e2e='profile-avatar']").count() > 0 or "foryou" in page.url:
                break
        
        if captcha_detected:
            yield log_func("Cảnh báo: Phát hiện CAPTCHA của TikTok. Bạn cần kéo CAPTCHA bằng tay trên màn hình trình duyệt (chờ 15 giây)...")
            # Sleep 15s to let user solve it manually (as this is headed browser mode)
            time.sleep(15)
            
        # Dynamic polling for final status for another 5s
        final_status = LoginStatus.LOGGED_OUT
        for _ in range(10): # 10 * 0.5s = 5s
            url = page.url
            captcha_still_exists = page.locator("[id='captcha-wrapper']").count() > 0 or page.locator(".captcha-slider").count() > 0
            
            if captcha_still_exists:
                final_status = LoginStatus.CHECKPOINT
            elif page.locator("[data-e2e='profile-icon']").count() > 0 or page.locator("[data-e2e='profile-avatar']").count() > 0 or "foryou" in url:
                yield log_func("Đăng nhập TikTok thành công.")
                final_status = LoginStatus.LOGGED_IN
                break
            elif "locked" in page.content().lower() or "suspension" in page.content().lower():
                yield log_func("Tài khoản bị khóa hoặc vô hiệu hóa.")
                final_status = LoginStatus.DEAD
                break
            time.sleep(0.5)
        else:
            # Check final states after timeout
            url = page.url
            captcha_still_exists = page.locator("[id='captcha-wrapper']").count() > 0 or page.locator(".captcha-slider").count() > 0
            if captcha_still_exists:
                yield log_func("Không giải được CAPTCHA, chặn đăng nhập.")
                final_status = LoginStatus.CHECKPOINT
            elif page.locator("[data-e2e='profile-icon']").count() > 0 or page.locator("[data-e2e='profile-avatar']").count() > 0 or "foryou" in url:
                final_status = LoginStatus.LOGGED_IN
            elif "locked" in page.content().lower() or "suspension" in page.content().lower():
                final_status = LoginStatus.DEAD
            else:
                yield log_func("Không thấy báo thành công, giả định đăng nhập thất bại.")
                final_status = LoginStatus.LOGGED_OUT
                
        return final_status
    else:
        yield log_func("Không tìm thấy trường nhập tài khoản/mật khẩu TikTok.")
        return LoginStatus.LOGGED_OUT
