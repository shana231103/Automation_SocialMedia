import time
from typing import Generator, Dict, Any
from DrissionPage import ChromiumPage

def login_facebook(page: ChromiumPage, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, None]:
    yield log_func("Đang truy cập trang chủ Facebook...")
    page.get("https://www.facebook.com/")
    
    # Check if already logged in
    if page.ele("css:[role='feed']") or page.ele("css:[role='navigation']") or "facebook.com/home.php" in page.url:
        yield log_func("Đã phát hiện phiên đăng nhập sẵn có.")
        yield log_func("Trạng thái xác định: đã đăng nhập")
        return

    yield log_func("Nhập thông tin tài khoản Facebook...")
    email_input = page.ele("css:input[name='email']")
    pass_input = page.ele("css:input[name='pass']")
    
    if not email_input or not pass_input:
        yield log_func("Không tìm thấy trường nhập liệu Facebook. Thử tìm locator khác...")
        email_input = page.ele("#email")
        pass_input = page.ele("#pass")

    if email_input and pass_input:
        email_input.input(username)
        time.sleep(0.5)
        pass_input.input(password)
        time.sleep(0.5)
        
        # Locate the button with multiple selector fallbacks
        login_btn = None
        for selector in ["css:button[name='login']", "css:[data-testid='royal_login_button']", "css:button[type='submit']", "css:input[type='submit']"]:
            btn = page.ele(selector)
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
            
        yield log_func("Đang đợi Facebook xác thực (8 giây)...")
        time.sleep(8)
        
        # Check results
        url = page.url
        yield log_func(f"URL hiện tại: {url}")
        
        if "checkpoint" in url or "checkpoint" in page.html.lower():
            yield log_func("Tài khoản yêu cầu phê duyệt đăng nhập / 2FA.")
            yield log_func("Trạng thái xác định: checkpoint")
        elif "login" in url or "error" in url or page.ele("css:.login_error_box") or page.ele("css:[id='error_box']"):
            yield log_func("Đăng nhập thất bại. Sai tài khoản mật khẩu hoặc bị chặn.")
            yield log_func("Trạng thái xác định: chưa đăng nhập")
        elif page.ele("css:[role='feed']") or page.ele("css:[role='navigation']") or "home" in url or "feed" in url or "facebook.com/home.php" in url:
            yield log_func("Đăng nhập thành công vào trang chủ.")
            yield log_func("Trạng thái xác định: đã đăng nhập")
        elif "disabled" in url or "suspended" in url or "locked" in page.html.lower():
            yield log_func("Tài khoản Facebook đã bị vô hiệu hóa.")
            yield log_func("Trạng thái xác định: dead")
        else:
            # Catch-all check
            yield log_func("Không rõ trạng thái cụ thể, mặc định chưa đăng nhập.")
            yield log_func("Trạng thái xác định: chưa đăng nhập")
    else:
        yield log_func("Không thể định vị được ô nhập tài khoản/mật khẩu.")
        yield log_func("Trạng thái xác định: chưa đăng nhập")
