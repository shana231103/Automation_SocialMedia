# File: backend/app/infrastructure/automation/platforms/youtube.py
"""Driver-agnostic YouTube/Google login automation script."""

import time
from typing import Generator, Dict, Any
from app.domain.models import LoginStatus
from app.infrastructure.automation.page_wrapper import AutomationPage

def login_youtube(page: AutomationPage, username: str, password: str, log_func) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Đang truy cập Google / YouTube Sign In...")
    page.goto("https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/")
    
    # Check if already logged in
    if "youtube.com" in page.url and page.find("css:#avatar-btn", timeout=2):
        yield log_func("Đã phát hiện phiên đăng nhập Google sẵn có.")
        return LoginStatus.LOGGED_IN

    yield log_func("Đang nhập Email...")
    email_input = page.find("css:input[type='email']", timeout=5)
    if not email_input:
        email_input = page.find("#identifierId", timeout=2)
        
    if not email_input:
        email_input = page.find_with_ai_fallback(
            "css:input[type='email']", "Google email input", timeout=2
        )

    if email_input:
        email_input.input(username)
        time.sleep(1)
        
        # Click next using find_first
        next_btn = page.find_first("css:#identifierNext", "text:Tiếp theo", "text:Next", timeout=3)
        if next_btn:
            next_btn.click()
        else:
            email_input.press("Enter")
            
        yield log_func("Đang chờ ô nhập Mật khẩu xuất hiện (chờ động)...")
        
        # Wait dynamically for password or account error
        pass_input = None
        account_error = False
        for _ in range(16): # up to 8s
            pass_input = page.find("css:input[type='password']", timeout=0.1)
            # Check if username error
            if page.find("text:Không thể tìm thấy Tài khoản Google", timeout=0.1) or page.find("text:Couldn't find your Google Account", timeout=0.1):
                account_error = True
                break
            if pass_input:
                break
            time.sleep(0.5)
            
        if not pass_input and not account_error:
            pass_input = page.find_with_ai_fallback(
                "css:input[type='password']", "Google password input", timeout=2
            )

        if account_error:
            yield log_func("Sai email hoặc tài khoản Google không tồn tại.")
            return LoginStatus.LOGGED_OUT
            
        if pass_input:
            yield log_func("Đang nhập Mật khẩu...")
            pass_input.input(password)
            time.sleep(1)
            
            next_btn2 = page.find_first("css:#passwordNext", "text:Tiếp theo", "text:Next", timeout=3)
            if next_btn2:
                next_btn2.click()
            else:
                pass_input.press("Enter")
                
            yield log_func("Đang đợi xác thực từ Google (chờ động tối đa 10 giây)...")
            
            # Dynamic polling for authentication result
            final_status = LoginStatus.LOGGED_OUT
            for _ in range(20): # up to 10s
                time.sleep(0.5)
                url = page.url
                
                # Check for 2FA / verification challenge
                if "signin/v2/challenge" in url or "signin/challenge" in url or "twofactor" in url or page.find("text:Xác minh danh tính", timeout=0.1) or page.find("text:Verify it's you", timeout=0.1):
                    yield log_func("Phát hiện yêu cầu xác minh bảo mật / mã 2FA từ Google. Vui lòng thực hiện xác minh trực tiếp trên trình duyệt (Chờ tối đa 60 giây)...")
                    
                    # Wait for user to complete 2FA for up to 60s (120 * 0.5s)
                    solved_2fa = False
                    for _ in range(120):
                        time.sleep(0.5)
                        url = page.url
                        if "youtube.com" in url or page.find("css:#avatar-btn", timeout=0.1) or page.find("css:ytd-app", timeout=0.1):
                            yield log_func("Đăng nhập Google / YouTube thành công sau xác minh.")
                            final_status = LoginStatus.LOGGED_IN
                            solved_2fa = True
                            break
                        if "disabled" in url or page.find("text:Tài khoản của bạn đã bị vô hiệu hóa", timeout=0.1) or page.find("text:Your account has been disabled", timeout=0.1):
                            yield log_func("Tài khoản Google đã bị vô hiệu hóa.")
                            final_status = LoginStatus.DEAD
                            solved_2fa = True
                            break
                            
                    if solved_2fa:
                        break
                    else:
                        yield log_func("Hết thời gian chờ người dùng thực hiện xác minh 2FA / bảo mật.")
                        final_status = LoginStatus.CHECKPOINT
                        break
                        
                elif "disabled" in url or page.find("text:Tài khoản của bạn đã bị vô hiệu hóa", timeout=0.1) or page.find("text:Your account has been disabled", timeout=0.1):
                    yield log_func("Tài khoản Google đã bị vô hiệu hóa.")
                    final_status = LoginStatus.DEAD
                    break
                elif "youtube.com" in url or page.find("css:#avatar-btn", timeout=0.1) or page.find("css:ytd-app", timeout=0.1):
                    yield log_func("Đăng nhập Google / YouTube thành công.")
                    final_status = LoginStatus.LOGGED_IN
                    break
                elif page.find("text:Mật khẩu không chính xác", timeout=0.1) or page.find("text:Wrong password", timeout=0.1):
                    yield log_func("Mật khẩu không chính xác hoặc lỗi đăng nhập.")
                    final_status = LoginStatus.LOGGED_OUT
                    break
            else:
                # Fallback check after timeout
                url = page.url
                yield log_func(f"Hết thời gian chờ Google. URL hiện tại: {url}")
                if "signin/v2/challenge" in url or "signin/challenge" in url or "twofactor" in url or page.find("text:Xác minh danh tính", timeout=1) or page.find("text:Verify it's you", timeout=1):
                    final_status = LoginStatus.CHECKPOINT
                elif "disabled" in url or page.find("text:Tài khoản của bạn đã bị vô hiệu hóa", timeout=1) or page.find("text:Your account has been disabled", timeout=1):
                    final_status = LoginStatus.DEAD
                elif "youtube.com" in url or page.find("css:#avatar-btn", timeout=1) or page.find("css:ytd-app", timeout=1):
                    final_status = LoginStatus.LOGGED_IN
                elif page.find("text:Mật khẩu không chính xác", timeout=1) or page.find("text:Wrong password", timeout=1) or "signin" in url:
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
