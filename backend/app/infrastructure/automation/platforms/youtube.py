import time
from typing import Generator, Dict, Any
from DrissionPage import ChromiumPage

def login_youtube(page: ChromiumPage, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, None]:
    yield log_func("Đang truy cập Google / YouTube Sign In...")
    # Direct URL to google login for youtube
    page.get("https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/")
    
    # Check if already logged in
    if "youtube.com" in page.url and page.ele("css:#avatar-btn"):
        yield log_func("Đã phát hiện phiên đăng nhập Google sẵn có.")
        yield log_func("Trạng thái xác định: đã đăng nhập")
        return

    yield log_func("Đang nhập Email...")
    email_input = page.ele("css:input[type='email']")
    if not email_input:
        email_input = page.ele("#identifierId")
        
    if email_input:
        email_input.input(username)
        time.sleep(1)
        
        # Click next
        next_btn = page.ele("css:#identifierNext") or page.ele("text:Tiếp theo") or page.ele("text:Next")
        if next_btn:
            next_btn.click()
        else:
            email_input.input("\n")
            
        yield log_func("Đang chờ ô nhập Mật khẩu xuất hiện...")
        time.sleep(4)
        
        # Check if username error
        if page.ele("text:Không thể tìm thấy Tài khoản Google") or page.ele("text:Couldn't find your Google Account"):
            yield log_func("Sai email hoặc tài khoản Google không tồn tại.")
            yield log_func("Trạng thái xác định: chưa đăng nhập")
            return
            
        pass_input = page.ele("css:input[type='password']")
        if pass_input:
            yield log_func("Đang nhập Mật khẩu...")
            pass_input.input(password)
            time.sleep(1)
            
            next_btn2 = page.ele("css:#passwordNext") or page.ele("text:Tiếp theo") or page.ele("text:Next")
            if next_btn2:
                next_btn2.click()
            else:
                pass_input.input("\n")
                
            yield log_func("Đang đợi xác thực từ Google (8 giây)...")
            time.sleep(8)
            
            url = page.url
            yield log_func(f"URL sau khi đăng nhập: {url}")
            
            # Check status
            if "signin/v2/challenge" in url or "signin/challenge" in url or "twofactor" in url or page.ele("text:Xác minh danh tính") or page.ele("text:Verify it's you"):
                yield log_func("Yêu cầu mã 2FA / Xác minh bảo mật.")
                yield log_func("Trạng thái xác định: checkpoint")
            elif "disabled" in url or page.ele("text:Tài khoản của bạn đã bị vô hiệu hóa") or page.ele("text:Your account has been disabled"):
                yield log_func("Tài khoản Google đã bị vô hiệu hóa.")
                yield log_func("Trạng thái xác định: dead")
            elif "youtube.com" in url or page.ele("css:#avatar-btn") or page.ele("css:ytd-app"):
                yield log_func("Đăng nhập Google / YouTube thành công.")
                yield log_func("Trạng thái xác định: đã đăng nhập")
            elif page.ele("text:Mật khẩu không chính xác") or page.ele("text:Wrong password") or "signin" in url:
                yield log_func("Mật khẩu không chính xác hoặc lỗi đăng nhập.")
                yield log_func("Trạng thái xác định: chưa đăng nhập")
            else:
                yield log_func("Không xác định được trạng thái rõ ràng.")
                yield log_func("Trạng thái xác định: chưa đăng nhập")
        else:
            yield log_func("Không tìm thấy ô nhập Mật khẩu. Có thể Google chặn bot/captcha.")
            yield log_func("Trạng thái xác định: checkpoint")
    else:
        yield log_func("Không thể tìm thấy ô nhập Email.")
        yield log_func("Trạng thái xác định: chưa đăng nhập")
