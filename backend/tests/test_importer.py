from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db import Base
from backend.app.main import app
from backend.app.models import Account, Trade, User
from backend.app.services.connectors import BrokerConfig, MetaTrader5Connector
from backend.app.services.importer import normalize_trade_row, upsert_trades


def _make_session() -> tuple[Session, int]:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    user = User(email="importer@example.com", hashed_password="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)

    account = Account(
        user_id=user.id,
        name="Importer Test Account",
        broker="MetaTrader 5",
        initial_balance=10000.0,
        current_balance=10100.0,
        currency="USD",
    )
    session.add(account)
    session.commit()
    session.refresh(account)

    return session, account.id


def test_normalize_trade_row():
    row = {
        "external_trade_id": "T-101",
        "symbol": "EURUSD",
        "side": "buy",
        "volume": "1.5",
        "entry_price": "1.0850",
        "exit_price": "1.0825",
        "stop_loss": "1.0838",
        "take_profit": "1.0900",
        "entry_time": "2026-09-29T10:00:00Z",
        "exit_time": "2026-09-29T10:15:00Z",
        "profit": "12.5",
        "commission": "0.5",
        "swap": "0.0",
        "net_profit": "12.0",
        "strategy": "Breakout",
        "session": "London",
    }

    normalized = normalize_trade_row(row, 1)

    assert normalized["symbol"] == "EURUSD"
    assert normalized["side"] == "long"
    assert normalized["risk_amount"] == 180.0
    assert normalized["r_multiple"] == 0.06666666666666667
    assert normalized["strategy_id"] == "Breakout"


def test_upsert_trades_prevents_duplicates():
    session, account_id = _make_session()

    row = {
        "external_trade_id": "dup-1",
        "symbol": "XAUUSD",
        "side": "sell",
        "volume": "1.0",
        "entry_price": "2338.0",
        "exit_price": "2333.0",
        "stop_loss": "2341.0",
        "take_profit": "2328.0",
        "net_profit": "-12.0",
        "strategy": "DAT",
        "session": "New York",
    }

    inserted, updated = upsert_trades(session, account_id, [row])
    assert (inserted, updated) == (1, 0)

    inserted_again, updated_again = upsert_trades(session, account_id, [row])
    assert (inserted_again, updated_again) == (0, 1)

    assert session.query(Trade).filter_by(account_id=account_id).count() == 1


def test_meta_trader_connector_reads_configured_trade_rows():
    config = BrokerConfig.from_json(
        {
            "broker": "MetaTrader 5",
            "account": "demo-001",
            "data": [
                {
                    "external_trade_id": "mt5-1",
                    "symbol": "EURUSD",
                    "side": "buy",
                    "volume": "1.0",
                    "entry_price": "1.1000",
                    "exit_price": "1.1040",
                    "stop_loss": "1.0970",
                    "take_profit": "1.1080",
                    "net_profit": "40.0",
                    "strategy_id": "Breakout",
                    "session": "London",
                }
            ],
        }
    )
    connector = MetaTrader5Connector(config)

    trades = connector.fetch_trades()

    assert len(trades) == 1
    assert trades[0]["symbol"] == "EURUSD"
    assert trades[0]["strategy_id"] == "Breakout"


def test_import_broker_trades_via_account_config():
    with TestClient(app) as client:
        register_result = client.post("/api/auth/register", json={"email": "broker@example.com", "password": "secret123"})
        assert register_result.status_code == 200
        token = register_result.json()["access_token"]

        account_result = client.post(
            "/api/accounts",
            json={
                "name": "Broker Demo",
                "broker": "MetaTrader 5",
                "connection_type": "mt5",
                "broker_config": '{"broker":"MetaTrader 5","data":[{"external_trade_id":"mt5-1","symbol":"EURUSD","side":"buy","volume":"1.0","entry_price":"1.1000","exit_price":"1.1040","stop_loss":"1.0970","take_profit":"1.1080","net_profit":"40.0","strategy_id":"Breakout","session":"London"}]}',
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert account_result.status_code == 200
        account = account_result.json()

        import_result = client.post(
            "/api/trades/import-broker",
            json={"account_id": account["id"]},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert import_result.status_code == 200
        assert import_result.json()["count"] == 1
