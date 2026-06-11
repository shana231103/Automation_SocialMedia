from datetime import datetime
from typing import Optional, List
from enum import Enum

class Platform(str, Enum):
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TWITTER = "twitter"

class LoginStatus(str, Enum):
    LOGGED_IN = "đã đăng nhập"
    LOGGED_OUT = "chưa đăng nhập"
    CHECKPOINT = "checkpoint"
    DEAD = "dead"

class Account:
    def __init__(
        self,
        id: Optional[int],
        username: str,
        password: str,
        platform: Platform,
        status: LoginStatus = LoginStatus.LOGGED_OUT,
        last_checked_at: Optional[datetime] = None
    ):
        self.id = id
        self.username = username
        self.password = password
        self.platform = platform
        self.status = status
        self.last_checked_at = last_checked_at

    def update_status(self, new_status: LoginStatus):
        self.status = new_status
        self.last_checked_at = datetime.now()

class LoginHistory:
    def __init__(
        self,
        id: Optional[int],
        account_id: Optional[int],
        platform: Platform,
        status: LoginStatus,
        run_logs: str,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.account_id = account_id
        self.platform = platform
        self.status = status
        self.run_logs = run_logs
        self.created_at = created_at or datetime.now()
