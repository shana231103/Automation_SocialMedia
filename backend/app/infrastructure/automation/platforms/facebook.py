import time
from typing import Generator, Dict, Any
from DrissionPage import ChromiumPage
from app.domain.models import LoginStatus

def login_facebook(page: ChromiumPage, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Đang truy cập trang chủ Facebook...")
    page.get("https://www.facebook.com/")
    
    # Check if already logged in
    if page.ele("css:[role='feed']", timeout=2) or page.ele("css:[role='navigation']", timeout=2) or "facebook.com/home.php" in page.url:
        yield log_func("Đã phát hiện phiên đăng nhập sẵn có.")
        return LoginStatus.LOGGED_IN

    yield log_func("Nhập thông tin tài khoản Facebook...")
    email_input = page.ele("css:input[name='email']", timeout=5)
    pass_input = page.ele("css:input[name='pass']", timeout=5)
    
    if not email_input or not pass_input:
        yield log_func("Không tìm thấy trường nhập liệu Facebook. Thử tìm locator khác...")
        email_input = page.ele("#email", timeout=2)
        pass_input = page.ele("#pass", timeout=2)

    if email_input and pass_input:
        email_input.input(username)
        time.sleep(0.5)
        pass_input.input(password)
        time.sleep(0.5)
        
        # Locate the button with multiple selector fallbacks
        login_btn = None
        for selector in ["css:button[name='login']", "css:[data-testid='royal_login_button']", "css:button[type='submit']", "css:input[type='submit']"]:
            btn = page.ele(selector, timeout=1)
            if btn:
                login_btn = btn
                break
                
        if login_btn:
            try:
                yield log_func("Click nút Đăng nhập...")
                login_btn.click()
            except Exception as e:
                yield log_func(f"Click thường thất bại ({str(e)}), thử click bằng JS...")
                try:
                    login_btn.click(by_js=True)
                except Exception as ex:
                    yield log_func(f"Click JS thất bại ({str(ex)}), gửi phím Enter trên ô mật khẩu...")
                    pass_input.input("\n")
        else:
            yield log_func("Không tìm thấy nút đăng nhập, gửi phím Enter trên ô mật khẩu...")
            pass_input.input("\n")
            
        yield log_func("Chờ 10 giây để người dùng giải CAPTCHA (nếu có)...")
        time.sleep(10)
            
        yield log_func("Đang đợi Facebook xác thực (chờ động tối đa 10 giây)...")
        
        # Dynamic polling
        final_status = LoginStatus.LOGGED_OUT
        for i in range(20): # 20 * 0.5s = 10s
            time.sleep(0.5)
            url = page.url
            if "checkpoint" in url:
                yield log_func("Tài khoản yêu cầu phê duyệt đăng nhập / 2FA.")
                final_status = LoginStatus.CHECKPOINT
                break
            elif "login" in url or "error" in url or page.ele("css:.login_error_box", timeout=0.1) or page.ele("css:[id='error_box']", timeout=0.1):
                yield log_func("Đăng nhập thất bại. Sai tài khoản mật khẩu hoặc bị chặn.")
                final_status = LoginStatus.LOGGED_OUT
                break
            elif page.ele("css:[role='feed']", timeout=0.1) or page.ele("css:[role='navigation']", timeout=0.1) or "home" in url or "feed" in url or "facebook.com/home.php" in url:
                yield log_func("Đăng nhập thành công vào trang chủ.")
                final_status = LoginStatus.LOGGED_IN
                break
            elif "disabled" in url or "suspended" in url or "locked" in page.html.lower():
                yield log_func("Tài khoản Facebook đã bị vô hiệu hóa.")
                final_status = LoginStatus.DEAD
                break
        else:
            # Check final states after timeout
            url = page.url
            yield log_func(f"Hết thời gian chờ động. URL hiện tại: {url}")
            if "checkpoint" in url:
                final_status = LoginStatus.CHECKPOINT
            elif page.ele("css:[role='feed']", timeout=1) or page.ele("css:[role='navigation']", timeout=1) or "home" in url or "feed" in url or "facebook.com/home.php" in url:
                final_status = LoginStatus.LOGGED_IN
            elif "disabled" in url or "suspended" in url or "locked" in page.html.lower():
                final_status = LoginStatus.DEAD
            else:
                final_status = LoginStatus.LOGGED_OUT
                yield log_func("Không rõ trạng thái cụ thể, mặc định chưa đăng nhập.")
                
        return final_status
    else:
        yield log_func("Không thể định vị được ô nhập tài khoản/mật khẩu.")
        return LoginStatus.LOGGED_OUT
