import time
from typing import Generator, Dict, Any
from DrissionPage import ChromiumPage

def login_tiktok(page: ChromiumPage, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, None]:
    yield log_func("Đang truy cập trang đăng nhập TikTok...")
    page.get("https://www.tiktok.com/login/phone-or-email/email")
    
    # Check if already logged in
    if "tiktok.com" in page.url and (page.ele("css:[data-e2e='profile-icon']") or page.ele("css:[data-e2e='profile-avatar']")):
        yield log_func("Đã phát hiện phiên đăng nhập TikTok sẵn có.")
        yield log_func("Trạng thái xác định: đã đăng nhập")
        return
        
    yield log_func("Đang nhập tài khoản email/username TikTok...")
    user_input = page.ele("css:input[name='username']")
    pass_input = page.ele("css:input[type='password']")
    
    if user_input and pass_input:
        user_input.input(username)
        time.sleep(0.5)
        pass_input.input(password)
        time.sleep(0.5)
        
        yield log_func("Click đăng nhập...")
        submit_btn = page.ele("css:button[type='submit']")
        if submit_btn:
            submit_btn.click()
        else:
            pass_input.input("\n")
            
        yield log_func("Đang chờ TikTok xử lý và hiển thị CAPTCHA nếu có (10 giây)...")
        time.sleep(10)
        
        # Check if captcha is visible
        captcha = page.ele("css:[id='captcha-wrapper']") or page.ele("css:.captcha-slider") or "captcha" in page.html.lower()
        if captcha:
            yield log_func("Cảnh báo: Phát hiện CAPTCHA của TikTok. Bạn cần kéo CAPTCHA bằng tay trên màn hình trình duyệt...")
            # Sleep another 15s to let user solve it manually if they want to
            time.sleep(15)
            
        url = page.url
        yield log_func(f"URL hiện tại: {url}")
        
        # Recheck captcha
        captcha_still_exists = page.ele("css:[id='captcha-wrapper']") or page.ele("css:.captcha-slider")
        
        if captcha_still_exists:
            yield log_func("Không giải được CAPTCHA, chặn đăng nhập.")
            yield log_func("Trạng thái xác định: checkpoint")
        elif page.ele("css:[data-e2e='profile-icon']") or page.ele("css:[data-e2e='profile-avatar']") or "foryou" in url:
            yield log_func("Đăng nhập TikTok thành công.")
            yield log_func("Trạng thái xác định: đã đăng nhập")
        elif "locked" in page.html.lower() or "suspension" in page.html.lower():
            yield log_func("Tài khoản bị khóa hoặc vô hiệu hóa.")
            yield log_func("Trạng thái xác định: dead")
        else:
            yield log_func("Không thấy báo thành công, giả định đăng nhập thất bại.")
            yield log_func("Trạng thái xác định: chưa đăng nhập")
    else:
        yield log_func("Không tìm thấy trường nhập tài khoản/mật khẩu TikTok.")
        yield log_func("Trạng thái xác định: chưa đăng nhập")
