import time
from typing import Generator, Dict, Any
from DrissionPage import ChromiumPage
from app.domain.models import LoginStatus

def login_youtube(page: ChromiumPage, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Đang truy cập Google / YouTube Sign In...")
    page.get("https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/")
    
    # Check if already logged in
    if "youtube.com" in page.url and page.ele("css:#avatar-btn", timeout=2):
        yield log_func("Đã phát hiện phiên đăng nhập Google sẵn có.")
        return LoginStatus.LOGGED_IN

    yield log_func("Đang nhập Email...")
    email_input = page.ele("css:input[type='email']", timeout=5)
    if not email_input:
        email_input = page.ele("#identifierId", timeout=2)
        
    if email_input:
        email_input.input(username)
        time.sleep(1)
        
        # Click next
        next_btn = page.ele("css:#identifierNext", timeout=1) or page.ele("text:Tiếp theo", timeout=1) or page.ele("text:Next", timeout=1)
        if next_btn:
            next_btn.click()
        else:
            email_input.input("\n")
            
        yield log_func("Đang chờ ô nhập Mật khẩu xuất hiện (chờ động)...")
        
        # Wait dynamically for password or account error
        pass_input = None
        account_error = False
        for _ in range(16): # up to 8s
            pass_input = page.ele("css:input[type='password']", timeout=0.1)
            # Check if username error
            if page.ele("text:Không thể tìm thấy Tài khoản Google", timeout=0.1) or page.ele("text:Couldn't find your Google Account", timeout=0.1):
                account_error = True
                break
            if pass_input:
                break
            time.sleep(0.5)
            
        if account_error:
            yield log_func("Sai email hoặc tài khoản Google không tồn tại.")
            return LoginStatus.LOGGED_OUT
            
        if pass_input:
            yield log_func("Đang nhập Mật khẩu...")
            pass_input.input(password)
            time.sleep(1)
            
            next_btn2 = page.ele("css:#passwordNext", timeout=1) or page.ele("text:Tiếp theo", timeout=1) or page.ele("text:Next", timeout=1)
            if next_btn2:
                next_btn2.click()
            else:
                pass_input.input("\n")
                
            yield log_func("Đang đợi xác thực từ Google (chờ động tối đa 10 giây)...")
            
            # Dynamic polling for authentication result
            final_status = LoginStatus.LOGGED_OUT
            for _ in range(20): # up to 10s
                time.sleep(0.5)
                url = page.url
                if "signin/v2/challenge" in url or "signin/challenge" in url or "twofactor" in url or page.ele("text:Xác minh danh tính", timeout=0.1) or page.ele("text:Verify it's you", timeout=0.1):
                    yield log_func("Yêu cầu mã 2FA / Xác minh bảo mật.")
                    final_status = LoginStatus.CHECKPOINT
                    break
                elif "disabled" in url or page.ele("text:Tài khoản của bạn đã bị vô hiệu hóa", timeout=0.1) or page.ele("text:Your account has been disabled", timeout=0.1):
                    yield log_func("Tài khoản Google đã bị vô hiệu hóa.")
                    final_status = LoginStatus.DEAD
                    break
                elif "youtube.com" in url or page.ele("css:#avatar-btn", timeout=0.1) or page.ele("css:ytd-app", timeout=0.1):
                    yield log_func("Đăng nhập Google / YouTube thành công.")
                    final_status = LoginStatus.LOGGED_IN
                    break
                elif page.ele("text:Mật khẩu không chính xác", timeout=0.1) or page.ele("text:Wrong password", timeout=0.1):
                    yield log_func("Mật khẩu không chính xác hoặc lỗi đăng nhập.")
                    final_status = LoginStatus.LOGGED_OUT
                    break
            else:
                # Fallback check after timeout
                url = page.url
                yield log_func(f"Hết thời gian chờ Google. URL hiện tại: {url}")
                if "signin/v2/challenge" in url or "signin/challenge" in url or "twofactor" in url or page.ele("text:Xác minh danh tính", timeout=1) or page.ele("text:Verify it's you", timeout=1):
                    final_status = LoginStatus.CHECKPOINT
                elif "disabled" in url or page.ele("text:Tài khoản của bạn đã bị vô hiệu hóa", timeout=1) or page.ele("text:Your account has been disabled", timeout=1):
                    final_status = LoginStatus.DEAD
                elif "youtube.com" in url or page.ele("css:#avatar-btn", timeout=1) or page.ele("css:ytd-app", timeout=1):
                    final_status = LoginStatus.LOGGED_IN
                elif page.ele("text:Mật khẩu không chính xác", timeout=1) or page.ele("text:Wrong password", timeout=1) or "signin" in url:
                    final_status = LoginStatus.LOGGED_OUT
                else:
                    yield log_func("Không xác định được trạng thái rõ ràng.")
                    final_status = LoginStatus.LOGGED_OUT
            return final_status
        else:
            yield log_func("Không tìm thấy ô nhập Mật khẩu. Có thể Google chặn bot/captcha.")
            return LoginStatus.CHECKPOINT
    else:
        yield log_func("Không thể tìm thấy ô nhập Email.")
        return LoginStatus.LOGGED_OUT
