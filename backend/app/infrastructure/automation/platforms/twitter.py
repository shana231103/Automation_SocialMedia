import time
from typing import Generator, Dict, Any
from DrissionPage import ChromiumPage

def login_twitter(page: ChromiumPage, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, None]:
    yield log_func("Đang truy cập trang đăng nhập X (Twitter)...")
    page.get("https://x.com/i/flow/login")
    
    # Check if already logged in
    if "x.com/home" in page.url or page.ele("css:[data-testid='AppTabBar_Home_Link']"):
        yield log_func("Đã phát hiện phiên đăng nhập X sẵn có.")
        yield log_func("Trạng thái xác định: đã đăng nhập")
        return
        
    yield log_func("Đang đợi ô nhập tên tài khoản xuất hiện...")
    time.sleep(5)
    
    username_input = page.ele("css:input[autocomplete='username']")
    if username_input:
        yield log_func("Đang nhập tên tài khoản...")
        username_input.input(username)
        time.sleep(0.5)
        
        # Click next button
        next_btn = page.ele("text:Next") or page.ele("text:Tiếp theo") or page.ele("xpath://span[text()='Next']")
        if next_btn:
            next_btn.click()
        else:
            username_input.input("\n")
            
        yield log_func("Đang đợi trường mật khẩu xuất hiện...")
        time.sleep(4)
        
        # Sometimes X asks for confirmation (phone/email check) before password
        confirmation_input = page.ele("css:input[data-testid='ocfEnterTextTextInput']")
        if confirmation_input:
            yield log_func("X yêu cầu xác minh email/sđt do đăng nhập bất thường.")
            yield log_func("Trạng thái xác định: checkpoint")
            return
            
        pass_input = page.ele("css:input[name='password']")
        if pass_input:
            yield log_func("Đang nhập mật khẩu...")
            pass_input.input(password)
            time.sleep(0.5)
            
            login_btn = page.ele("css:button[data-testid='LoginForm_Login_Button']") or page.ele("text:Log in") or page.ele("text:Đăng nhập")
            if login_btn:
                login_btn.click()
            else:
                pass_input.input("\n")
                
            yield log_func("Đang đợi X xác thực (8 giây)...")
            time.sleep(8)
            
            url = page.url
            yield log_func(f"URL sau đăng nhập X: {url}")
            
            # Check status
            if "home" in url or page.ele("css:[data-testid='AppTabBar_Home_Link']"):
                yield log_func("Đăng nhập X (Twitter) thành công.")
                yield log_func("Trạng thái xác định: đã đăng nhập")
            elif "account-suspended" in url or "suspended" in page.html.lower():
                yield log_func("Tài khoản X bị đình chỉ/suspension.")
                yield log_func("Trạng thái xác định: dead")
            elif "checkpoint" in url or "challenge" in url or page.ele("text:Xác thực tài khoản của bạn") or page.ele("text:Authenticate your account"):
                yield log_func("Tài khoản X yêu cầu xác thực bảo mật / CAPTCHA.")
                yield log_func("Trạng thái xác định: checkpoint")
            else:
                yield log_func("Sai thông tin đăng nhập hoặc lỗi đăng nhập.")
                yield log_func("Trạng thái xác định: chưa đăng nhập")
        else:
            yield log_func("Không tìm thấy ô nhập mật khẩu X. Có thể do lỗi tải trang hoặc bị chặn.")
            yield log_func("Trạng thái xác định: chưa đăng nhập")
    else:
        yield log_func("Không tìm thấy ô nhập tên tài khoản X (có thể do lỗi Cloudflare hoặc mạng chậm).")
        yield log_func("Trạng thái xác định: chưa đăng nhập")
