import time
from typing import Generator, Dict, Any
from DrissionPage import ChromiumPage
from app.domain.models import LoginStatus

def login_twitter(page: ChromiumPage, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Đang truy cập trang đăng nhập X (Twitter)...")
    page.get("https://x.com/i/flow/login")
    
    # Check if already logged in
    if "x.com/home" in page.url or page.ele("css:[data-testid='AppTabBar_Home_Link']", timeout=2):
        yield log_func("Đã phát hiện phiên đăng nhập X sẵn có.")
        return LoginStatus.LOGGED_IN
        
    yield log_func("Đang đợi ô nhập tên tài khoản xuất hiện (chờ động)...")
    
    # Wait for username input dynamically
    username_input = None
    for _ in range(16): # up to 8s
        for selector in ["css:input[name='text']", "css:input[autocomplete='username']", "css:input[type='text']", "xpath://input[@name='text']"]:
            username_input = page.ele(selector, timeout=0.1)
            if username_input:
                break
        if username_input:
            break
        time.sleep(0.5)
        
    if username_input:
        yield log_func("Đang nhập tên tài khoản...")
        username_input.input(username)
        time.sleep(0.5)
        
        # Click next button
        next_btn = None
        for selector in [
            "text:Next", 
            "text:Tiếp theo", 
            "xpath://span[text()='Next']", 
            "xpath://span[text()='Tiếp theo']",
            "xpath://button[.//span[text()='Next']]",
            "xpath://button[.//span[text()='Tiếp theo']]"
        ]:
            btn = page.ele(selector, timeout=0.5)
            if btn:
                next_btn = btn
                break
                
        if next_btn:
            next_btn.click()
        else:
            username_input.input("\n")
            
        yield log_func("Đang đợi trường mật khẩu hoặc xác minh xuất hiện...")
        
        # Wait dynamically for password or confirmation input
        pass_input = None
        confirmation_input = None
        for _ in range(16): # up to 8s
            pass_input = page.ele("css:input[name='password']", timeout=0.1)
            confirmation_input = page.ele("css:input[data-testid='ocfEnterTextTextInput']", timeout=0.1)
            if pass_input or confirmation_input:
                break
            time.sleep(0.5)
        
        if confirmation_input:
            yield log_func("X yêu cầu xác minh email/sđt do đăng nhập bất thường.")
            return LoginStatus.CHECKPOINT
            
        if pass_input:
            yield log_func("Đang nhập mật khẩu...")
            pass_input.input(password)
            time.sleep(0.5)
            
            login_btn = page.ele("css:button[data-testid='LoginForm_Login_Button']", timeout=1) or page.ele("text:Log in", timeout=1) or page.ele("text:Đăng nhập", timeout=1)
            if login_btn:
                login_btn.click()
            else:
                pass_input.input("\n")
                
            yield log_func("Đang đợi X xác thực (chờ động tối đa 10 giây)...")
            
            # Dynamic polling for final status
            final_status = LoginStatus.LOGGED_OUT
            for _ in range(20): # up to 10s
                time.sleep(0.5)
                url = page.url
                if "home" in url or page.ele("css:[data-testid='AppTabBar_Home_Link']", timeout=0.1):
                    yield log_func("Đăng nhập X (Twitter) thành công.")
                    final_status = LoginStatus.LOGGED_IN
                    break
                elif "account-suspended" in url or "suspended" in url:
                    yield log_func("Tài khoản X bị đình chỉ/suspension.")
                    final_status = LoginStatus.DEAD
                    break
                elif "checkpoint" in url or "challenge" in url or page.ele("text:Xác thực tài khoản của bạn", timeout=0.1) or page.ele("text:Authenticate your account", timeout=0.1):
                    yield log_func("Tài khoản X yêu cầu xác thực bảo mật / CAPTCHA.")
                    final_status = LoginStatus.CHECKPOINT
                    break
            else:
                # Fallback check after timeout
                url = page.url
                yield log_func(f"Hết thời gian chờ động X. URL hiện tại: {url}")
                if "home" in url or page.ele("css:[data-testid='AppTabBar_Home_Link']", timeout=1):
                    final_status = LoginStatus.LOGGED_IN
                elif "account-suspended" in url or "suspended" in url:
                    final_status = LoginStatus.DEAD
                elif "checkpoint" in url or "challenge" in url or page.ele("text:Xác thực tài khoản của bạn", timeout=1) or page.ele("text:Authenticate your account", timeout=1):
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
