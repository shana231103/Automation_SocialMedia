from typing import Generator, Dict, Any
from app.domain.models import LoginHistory, LoginStatus
from app.domain.repositories import AccountRepository, LoginHistoryRepository
from app.application.interfaces import AutomationService

class RunLoginUseCase:
    def __init__(
        self,
        account_repo: AccountRepository,
        history_repo: LoginHistoryRepository,
        automation_service: AutomationService
    ):
        self.account_repo = account_repo
        self.history_repo = history_repo
        self.automation_service = automation_service

    def execute(self, account_id: int) -> Generator[Dict[str, Any], None, None]:
        account = self.account_repo.get_by_id(account_id)
        if not account:
            yield {"type": "error", "message": f"Tài khoản ID {account_id} không tồn tại."}
            return

        yield {"type": "log", "message": f"Bắt đầu chạy automation đăng nhập cho {account.platform.value} ({account.username})..."}
        
        final_status = None
        full_logs = ""
        
        try:
            # Stream logs from automation service
            for progress in self.automation_service.run_login(account.username, account.password, account.platform):
                if progress["type"] == "log":
                    yield progress
                elif progress["type"] == "result":
                    final_status = progress["status"]
                    full_logs = progress["logs"]
                    yield progress
        except Exception as e:
            error_msg = f"Lỗi không mong muốn trong quá trình chạy: {str(e)}"
            yield {"type": "log", "message": error_msg}
            final_status = LoginStatus.LOGGED_OUT
            full_logs = f"System Error:\n{str(e)}"
            yield {"type": "result", "status": final_status, "logs": full_logs}

        if final_status:
            # Convert to LoginStatus enum instance in case it is yielded as a string
            status_enum = LoginStatus(final_status)
            
            # Update account status
            account.update_status(status_enum)
            self.account_repo.save(account)
            
            # Save history
            history = LoginHistory(
                id=None,
                account_id=account.id,
                platform=account.platform,
                status=status_enum,
                run_logs=full_logs
            )
            self.history_repo.save(history)
            
            yield {"type": "log", "message": f"Đã cập nhật trạng thái tài khoản '{account.username}' thành: {status_enum.value}."}
            yield {"type": "done", "message": "Hoàn thành automation."}
