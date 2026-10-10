from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import Account, Trade


def create_demo_trades(db: Session, account_id: int) -> list[Trade]:
    if db.query(Trade).filter(Trade.account_id == account_id).count() > 0:
        return db.query(Trade).filter(Trade.account_id == account_id).all()

    now = datetime.utcnow()
    trades = [
        Trade(
            account_id=account_id,
            external_trade_id="demo-001",
            symbol="XAUUSD",
            side="long",
            volume=1.0,
            entry_price=2340.1,
            exit_price=2345.4,
            stop_loss=2338.5,
            take_profit=2348.0,
            entry_time=now - timedelta(days=6, hours=2),
            exit_time=now - timedelta(days=6, hours=1),
            profit=40.0,
            commission=0.0,
            swap=0.0,
            net_profit=40.0,
            risk_amount=20.0,
            r_multiple=2.0,
            strategy_id="Breakout",
            session="New York",
        ),
        Trade(
            account_id=account_id,
            external_trade_id="demo-002",
            symbol="EURUSD",
            side="short",
            volume=0.5,
            entry_price=1.085,
            exit_price=1.082,
            stop_loss=1.088,
            take_profit=1.079,
            entry_time=now - timedelta(days=5, hours=1),
            exit_time=now - timedelta(days=5, hours=0),
            profit=25.0,
            commission=0.0,
            swap=0.0,
            net_profit=25.0,
            risk_amount=18.0,
            r_multiple=1.39,
            strategy_id="Supply/Demand",
            session="London",
        ),
        Trade(
            account_id=account_id,
            external_trade_id="demo-003",
            symbol="GBPUSD",
            side="long",
            volume=1.2,
            entry_price=1.272,
            exit_price=1.268,
            stop_loss=1.267,
            take_profit=1.279,
            entry_time=now - timedelta(days=4, hours=3),
            exit_time=now - timedelta(days=4, hours=2),
            profit=-15.0,
            commission=0.0,
            swap=0.0,
            net_profit=-15.0,
            risk_amount=20.0,
            r_multiple=-0.75,
            strategy_id="EMA 8/30",
            session="London",
        ),
        Trade(
            account_id=account_id,
            external_trade_id="demo-004",
            symbol="BTCUSD",
            side="long",
            volume=0.1,
            entry_price=65500,
            exit_price=66050,
            stop_loss=64900,
            take_profit=66280,
            entry_time=now - timedelta(days=2, hours=5),
            exit_time=now - timedelta(days=2, hours=4),
            profit=55.0,
            commission=0.0,
            swap=0.0,
            net_profit=55.0,
            risk_amount=30.0,
            r_multiple=1.83,
            strategy_id="Swing",
            session="New York",
        ),
        Trade(
            account_id=account_id,
            external_trade_id="demo-005",
            symbol="XAUUSD",
            side="short",
            volume=1.0,
            entry_price=2338.2,
            exit_price=2332.0,
            stop_loss=2345.0,
            take_profit=2327.0,
            entry_time=now - timedelta(days=1, hours=6),
            exit_time=now - timedelta(days=1, hours=5),
            profit=-28.0,
            commission=0.0,
            swap=0.0,
            net_profit=-28.0,
            risk_amount=18.0,
            r_multiple=-1.56,
            strategy_id="DAT",
            session="London",
        ),
    ]
    db.add_all(trades)
    db.commit()
    for trade in trades:
        db.refresh(trade)
    return trades


def ensure_demo_account(db: Session, user_id: int) -> Account:
    account = db.query(Account).filter(Account.user_id == user_id).first()
    if account is not None:
        return account

    account = Account(
        user_id=user_id,
        name="Demo Prop Challenge",
        broker="MetaTrader 5",
        prop_firm="Demo Prop",
        account_number="DEMO-1001",
        initial_balance=10000.0,
        current_balance=10250.0,
        currency="USD",
        account_type="demo",
        status="active",
        connection_type="csv",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
