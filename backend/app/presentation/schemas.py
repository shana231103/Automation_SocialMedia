from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.domain.models import Platform, LoginStatus

class AccountCreate(BaseModel):
    username: str = Field(..., min_length=1, description="Username/Email of the account")
    password: str = Field(..., min_length=1, description="Password of the account")
    platform: Platform = Field(..., description="Social media platform")

class AccountResponse(BaseModel):
    id: int
    username: str
    platform: Platform
    status: LoginStatus
    last_checked_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class LoginHistoryResponse(BaseModel):
    id: int
    account_id: Optional[int]
    platform: Platform
    status: LoginStatus
    run_logs: str
    created_at: datetime

    class Config:
        from_attributes = True
