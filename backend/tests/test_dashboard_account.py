import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db import Base
from backend.app.main import dashboard_summary
from backend.app.models import Account, User


def _make_session() -> tuple[Session, User, Account, Account]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(email="owner@example.com", hashed_password="test")
    other_user = User(email="other@example.com", hashed_password="test")
    session.add_all([user, other_user])
    session.flush()
    owned_account = Account(user_id=user.id, name="Primary", initial_balance=5000.0)
    foreign_account = Account(user_id=other_user.id, name="Private", initial_balance=9000.0)
    session.add_all([owned_account, foreign_account])
    session.commit()
    return session, user, owned_account, foreign_account


def test_dashboard_returns_only_the_selected_owned_account():
    session, user, owned_account, _ = _make_session()

    result = dashboard_summary(owned_account.id, user, session)

    assert result["account"]["id"] == owned_account.id
    assert result["account"]["name"] == "Primary"
    assert result["metrics"]["total_trades"] == 0
    assert result["trades"] == []


def test_dashboard_rejects_an_account_owned_by_another_user():
    session, user, _, foreign_account = _make_session()

    with pytest.raises(HTTPException) as error:
        dashboard_summary(foreign_account.id, user, session)

    assert error.value.status_code == 404