from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.infrastructure.database.connection import Base

class DbAccount(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    status = Column(String, nullable=False, default="chưa đăng nhập")
    last_checked_at = Column(DateTime, nullable=True)


class DbLoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    platform = Column(String, nullable=False)
    status = Column(String, nullable=False)
    run_logs = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
