from typing import List, Optional
from sqlalchemy.orm import Session
from app.domain.models import Account, LoginHistory, Platform, LoginStatus
from app.domain.repositories import AccountRepository, LoginHistoryRepository
from app.infrastructure.database.models import DbAccount, DbLoginHistory

def to_domain_account(db_acc: DbAccount) -> Account:
    return Account(
        id=db_acc.id,
        username=db_acc.username,
        password=db_acc.password,
        platform=Platform(db_acc.platform),
        status=LoginStatus(db_acc.status),
        last_checked_at=db_acc.last_checked_at
    )

def to_domain_history(db_hist: DbLoginHistory) -> LoginHistory:
    return LoginHistory(
        id=db_hist.id,
        account_id=db_hist.account_id,
        platform=Platform(db_hist.platform),
        status=LoginStatus(db_hist.status),
        run_logs=db_hist.run_logs,
        created_at=db_hist.created_at
    )


class SqlAlchemyAccountRepository(AccountRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, account_id: int) -> Optional[Account]:
        db_acc = self.session.query(DbAccount).filter(DbAccount.id == account_id).first()
        return to_domain_account(db_acc) if db_acc else None

    def get_all(self) -> List[Account]:
        db_accounts = self.session.query(DbAccount).order_by(DbAccount.id.desc()).all()
        return [to_domain_account(acc) for acc in db_accounts]

    def save(self, account: Account) -> Account:
        if account.id is not None:
            # Update existing
            db_acc = self.session.query(DbAccount).filter(DbAccount.id == account.id).first()
            if db_acc:
                db_acc.username = account.username
                db_acc.password = account.password
                db_acc.platform = account.platform.value
                db_acc.status = account.status.value
                db_acc.last_checked_at = account.last_checked_at
        else:
            # Create new
            db_acc = DbAccount(
                username=account.username,
                password=account.password,
                platform=account.platform.value,
                status=account.status.value,
                last_checked_at=account.last_checked_at
            )
            self.session.add(db_acc)

        self.session.commit()
        self.session.refresh(db_acc)
        return to_domain_account(db_acc)

    def delete(self, account_id: int) -> bool:
        db_acc = self.session.query(DbAccount).filter(DbAccount.id == account_id).first()
        if db_acc:
            self.session.delete(db_acc)
            self.session.commit()
            return True
        return False


class SqlAlchemyLoginHistoryRepository(LoginHistoryRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, history: LoginHistory) -> LoginHistory:
        db_hist = DbLoginHistory(
            account_id=history.account_id,
            platform=history.platform.value,
            status=history.status.value,
            run_logs=history.run_logs,
            created_at=history.created_at
        )
        self.session.add(db_hist)
        self.session.commit()
        self.session.refresh(db_hist)
        return to_domain_history(db_hist)

    def get_all(self) -> List[LoginHistory]:
        db_history = self.session.query(DbLoginHistory).order_by(DbLoginHistory.created_at.desc()).all()
        return [to_domain_history(hist) for hist in db_history]

    def get_by_account_id(self, account_id: int) -> List[LoginHistory]:
        db_history = (
            self.session.query(DbLoginHistory)
            .filter(DbLoginHistory.account_id == account_id)
            .order_by(DbLoginHistory.created_at.desc())
            .all()
        )
        return [to_domain_history(hist) for hist in db_history]

    def clear_all(self) -> bool:
        try:
            self.session.query(DbLoginHistory).delete()
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            return False
