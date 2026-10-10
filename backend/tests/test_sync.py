from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db import Base
from backend.app.models import Account, SyncLog, User
from backend.app.services.connectors import TradeConnector
from backend.app.services.sync import sync_trades


def _make_session() -> tuple[Session, int]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    user = User(email="sync@example.com", hashed_password="test")
    session.add(user)
    session.flush()
    account = Account(user_id=user.id, name="Sync test", initial_balance=10000.0)
    session.add(account)
    session.commit()
    return session, account.id


class SuccessfulConnector:
    def fetch_trades(self) -> list[dict[str, str]]:
        return [{
            "external_trade_id": "sync-1",
            "symbol": "EURUSD",
            "side": "buy",
            "entry_price": "1.08",
            "exit_price": "1.09",
            "net_profit": "25",
        }]


class FailedConnector:
    def fetch_trades(self) -> list[dict[str, str]]:
        raise RuntimeError("connector unavailable")


def test_sync_trades_records_success_and_upsert_counts():
    session, account_id = _make_session()

    result = sync_trades(session, account_id, SuccessfulConnector())

    assert result.status == "success"
    assert result.trades_fetched == 1
    assert result.inserted == 1
    assert result.updated == 0
    assert result.ended_at is not None


def test_sync_trades_persists_failed_run_before_reraising():
    session, account_id = _make_session()

    try:
        sync_trades(session, account_id, FailedConnector())
    except RuntimeError as error:
        assert str(error) == "connector unavailable"
    else:
        raise AssertionError("expected connector error")

    log = session.query(SyncLog).filter_by(account_id=account_id).one()
    assert log.status == "failed"
    assert log.errors == "RuntimeError: connector unavailable"
    assert log.ended_at is not None