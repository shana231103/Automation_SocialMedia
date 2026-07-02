import time
from typing import Generator, Dict, Any
from playwright.sync_api import Page
from app.domain.models import LoginStatus

def login_twitter(page: Page, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Đang truy cập trang đăng nhập X (Twitter)...")
    page.goto("https://x.com/i/flow/login")
    
    # Check if already logged in
    if "x.com/home" in page.url or page.locator("[data-testid='AppTabBar_Home_Link']").count() > 0:
        yield log_func("Đã phát hiện phiên đăng nhập X sẵn có.")
        return LoginStatus.LOGGED_IN
        
    yield log_func("Đang đợi ô nhập tên tài khoản xuất hiện (chờ động)...")
    
    # Wait for username input dynamically
    username_input = None
    for _ in range(16): # up to 8s
        for selector in ["input[name='text']", "input[autocomplete='username']", "input[type='text']"]:
            btn = page.locator(selector)
            if btn.count() > 0:
                username_input = btn
                break
        if username_input:
            break
        time.sleep(0.5)
        
    if username_input:
        yield log_func("Đang nhập tên tài khoản...")
        username_input.fill(username)
        time.sleep(0.5)
        
        # Click next button
        next_btn = None
        for selector in [
            "text=Next", 
            "text=Tiếp theo", 
            "xpath=//span[text()='Next']", 
            "xpath=//span[text()='Tiếp theo']",
            "xpath=//button[.//span[text()='Next']]",
            "xpath=//button[.//span[text()='Tiếp theo']]"
        ]:
            btn = page.locator(selector)
            if btn.count() > 0:
                next_btn = btn
                break
                
        if next_btn:
            next_btn.click()
        else:
            username_input.press("Enter")
            
        yield log_func("Đang đợi trường mật khẩu hoặc xác minh xuất hiện...")
        
        # Wait dynamically for password or confirmation input
        pass_input = None
        confirmation_input = None
        for _ in range(16): # up to 8s
            pass_input = page.locator("input[name='password']")
            confirmation_input = page.locator("input[data-testid='ocfEnterTextTextInput']")
            if (pass_input.count() > 0 and pass_input.is_visible()) or (confirmation_input.count() > 0 and confirmation_input.is_visible()):
                break
            time.sleep(0.5)
        
        if confirmation_input and confirmation_input.count() > 0 and confirmation_input.is_visible():
            yield log_func("X yêu cầu xác minh email/sđt do đăng nhập bất thường.")
            return LoginStatus.CHECKPOINT
            
        if pass_input and pass_input.count() > 0 and pass_input.is_visible():
            yield log_func("Đang nhập mật khẩu...")
            pass_input.fill(password)
            time.sleep(0.5)
            
            login_btn = None
            for selector in ["button[data-testid='LoginForm_Login_Button']", "text=Log in", "text=Đăng nhập"]:
                btn = page.locator(selector)
                if btn.count() > 0:
                    login_btn = btn
                    break
            if login_btn:
                login_btn.click()
            else:
                pass_input.press("Enter")
                
            yield log_func("Đang đợi X xác thực (chờ động tối đa 10 giây)...")
            
            # Dynamic polling for final status
            final_status = LoginStatus.LOGGED_OUT
            for _ in range(20): # up to 10s
                time.sleep(0.5)
                url = page.url
                if "home" in url or page.locator("[data-testid='AppTabBar_Home_Link']").count() > 0:
                    yield log_func("Đăng nhập X (Twitter) thành công.")
                    final_status = LoginStatus.LOGGED_IN
                    break
                elif "account-suspended" in url or "suspended" in url:
                    yield log_func("Tài khoản X bị đình chỉ/suspension.")
                    final_status = LoginStatus.DEAD
                    break
                elif "checkpoint" in url or "challenge" in url or page.locator("text=Xác thực tài khoản của bạn").count() > 0 or page.locator("text=Authenticate your account").count() > 0:
                    yield log_func("Tài khoản X yêu cầu xác thực bảo mật / CAPTCHA.")
                    final_status = LoginStatus.CHECKPOINT
                    break
            else:
                # Fallback check after timeout
                url = page.url
                yield log_func(f"Hết thời gian chờ động X. URL hiện tại: {url}")
                if "home" in url or page.locator("[data-testid='AppTabBar_Home_Link']").count() > 0:
                    final_status = LoginStatus.LOGGED_IN
                elif "account-suspended" in url or "suspended" in url:
                    final_status = LoginStatus.DEAD
                elif "checkpoint" in url or "challenge" in url or page.locator("text=Xác thực tài khoản của bạn").count() > 0 or page.locator("text=Authenticate your account").count() > 0:
                    final_status = LoginStatus.CHECKPOINT
                else:
                    yield log_func("Sai thông tin đăng nhập hoặc lỗi đăng nhập.")
                    final_status = LoginStatus.LOGGED_OUT
            return final_status
        else:
            yield log_func("Không tìm thấy ô nhập mật khẩu X. Có thể do lỗi tải trang hoặc bị chặn.")
            return LoginStatus.LOGGED_OUT
    else:
        yield log_func("Không tìm thấy ô nhập tên tài khoản X (có thể do lỗi Cloudflare hoặc mạng chậm).")
        return LoginStatus.LOGGED_OUT
