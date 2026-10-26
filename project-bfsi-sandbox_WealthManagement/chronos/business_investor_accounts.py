"""Find an investor's account and describe its current state."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from chronos.storage_sqlite_tables_and_sessions import Account
from chronos.app_business_errors_and_permissions import (
    RecordNotFoundError,
    require_advisor_user,
    require_investor_user,
)
from chronos.app_demo_data_and_reset import (
    get_demo_user_by_id,
    login_demo_user_by_email,
)


def get_account_for_investor_user(db: Session, user_id: int) -> Account:
    require_investor_user(get_demo_user_by_id(db, user_id))
    account = db.scalar(select(Account).where(Account.user_id == user_id))
    if account is None:
        raise RecordNotFoundError(f"No account for user {user_id}")
    return account


def get_account_for_viewer(
    db: Session, user_id: int, investor_id: int | None = None
) -> Account:
    """Investors see their own account; the demo advisor opens Alice's account."""
    viewer = get_demo_user_by_id(db, user_id)
    if investor_id is None:
        investor_id = (
            login_demo_user_by_email(db, "alice@example.com").id
            if viewer.role == "ADVISOR"
            else viewer.id
        )
    if investor_id != viewer.id:
        require_advisor_user(viewer)
    return get_account_for_investor_user(db, investor_id)
