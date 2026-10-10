from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, ensure_sqlite_schema, get_db
from .models import Account, RiskRule, SyncLog, Trade, User
from .schemas import AccountCreate, AccountRead, RiskRuleRead, RiskRuleUpsert, SyncLogRead, Token, TradeRead, UserCreate
from .security import authenticate_user, create_access_token, get_current_user, get_password_hash
from .seed_demo import create_demo_trades, ensure_demo_account
from .services.analytics import calculate_drawdown, calculate_r_multiple, calculate_strategy_metrics, calculate_trade_metrics
from .services.analyst import generate_analyst_report
from .services.connectors import CsvTradeConnector, MetaTrader5Connector
from .services.risk import evaluate_risk
from .services.sync import sync_trades

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_sqlite_schema()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Trading Intelligence Dashboard", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=Token)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=payload.email, hashed_password=get_password_hash(payload.password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    return Token(access_token=create_access_token(str(user.id)))


@app.post("/api/auth/login", response_model=Token)
def login_user(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return Token(access_token=create_access_token(str(user.id)))


@app.get("/api/accounts", response_model=list[AccountRead])
def list_accounts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[AccountRead]:
    return db.query(Account).filter(Account.user_id == current_user.id).all()


@app.post("/api/accounts", response_model=AccountRead)
def create_account(payload: AccountCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Account:
    account = Account(user_id=current_user.id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@app.get("/api/trades", response_model=list[TradeRead])
def list_trades(
    account_id: int | None = Query(default=None),
    symbol: str | None = Query(default=None),
    strategy_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Trade]:
    query = db.query(Trade).join(Account).filter(Account.user_id == current_user.id)
    if account_id is not None:
        query = query.filter(Trade.account_id == account_id)
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    if strategy_id:
        query = query.filter(Trade.strategy_id == strategy_id)

    trades = query.order_by(Trade.entry_time.desc()).all()
    if not trades:
        account = ensure_demo_account(db, current_user.id)
        trades = create_demo_trades(db, account.id)
    return trades


@app.post("/api/trades/import-demo")
def import_demo_trades(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    account = ensure_demo_account(db, current_user.id)
    trades = create_demo_trades(db, account.id)
    return {"status": "ok", "account_id": account.id, "count": len(trades)}


@app.post("/api/trades/import-csv")
async def import_csv_trades(
    account_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    csv_text = (await file.read()).decode("utf-8-sig")
    sync_log = sync_trades(db, account.id, CsvTradeConnector(csv_text))

    return {
        "status": "ok",
        "account_id": account.id,
        "sync_id": sync_log.id,
        "inserted": sync_log.inserted,
        "updated": sync_log.updated,
        "total_rows": sync_log.trades_fetched,
    }


@app.post("/api/trades/import-broker")
def import_broker_trades(
    payload: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account_id = payload.get("account_id")
    if account_id is None:
        raise HTTPException(status_code=400, detail="account_id is required")

    account = db.query(Account).filter(Account.id == int(account_id), Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    config = account.broker_config or account.connection_type
    if not config or account.connection_type != "mt5":
        raise HTTPException(status_code=400, detail="This account is not configured for MetaTrader 5 import")

    sync_log = sync_trades(db, account.id, MetaTrader5Connector(str(config)))
    return {
        "status": "ok",
        "account_id": account.id,
        "sync_id": sync_log.id,
        "inserted": sync_log.inserted,
        "updated": sync_log.updated,
        "count": sync_log.trades_fetched,
    }


@app.get("/api/accounts/{account_id}/sync-logs", response_model=list[SyncLogRead])
def account_sync_history(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SyncLog]:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return db.query(SyncLog).filter(SyncLog.account_id == account.id).order_by(SyncLog.started_at.desc()).all()


@app.put("/api/accounts/{account_id}/risk-rules", response_model=RiskRuleRead)
def upsert_account_risk_rules(
    account_id: int,
    payload: RiskRuleUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskRule:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    rules = db.query(RiskRule).filter(RiskRule.account_id == account.id).first()
    if rules is None:
        rules = RiskRule(account_id=account.id, **payload.model_dump())
        db.add(rules)
    else:
        for field, value in payload.model_dump().items():
            setattr(rules, field, value)

    db.commit()
    db.refresh(rules)
    return rules


@app.get("/api/accounts/{account_id}/risk")
def account_risk_status(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    rules = db.query(RiskRule).filter(RiskRule.account_id == account.id).first()
    trades = db.query(Trade).filter(Trade.account_id == account.id).all()
    initial_balance = (rules.initial_balance if rules and rules.initial_balance > 0 else account.initial_balance) or 0.0
    return {
        "account_id": account.id,
        "rules": RiskRuleRead.model_validate(rules).model_dump() if rules else None,
        "assessment": evaluate_risk(trades, initial_balance, rules),
    }


@app.get("/api/analytics/dashboard")
def dashboard_summary(
    account_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account_query = db.query(Account).filter(Account.user_id == current_user.id)
    account = account_query.filter(Account.id == account_id).first() if account_id is not None else account_query.first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    trades = db.query(Trade).filter(Trade.account_id == account.id).all()

    metrics = calculate_trade_metrics(trades)
    equity_curve: list[float] = []
    running_total = float(account.initial_balance)
    for trade in sorted(trades, key=lambda t: t.entry_time or datetime.utcnow()):
        running_total += float(trade.net_profit or 0.0)
        equity_curve.append(running_total)

    drawdown = calculate_drawdown(equity_curve)
    dashboard = {
        "account": {"id": account.id, "name": account.name, "currency": account.currency},
        "metrics": {
            **metrics,
            "balance": float(account.current_balance or account.initial_balance),
            "equity": float(account.current_balance or account.initial_balance),
            "daily_pnl": sum(float(t.net_profit or 0.0) for t in trades),
            "max_drawdown": drawdown["maximum_drawdown"],
            "max_drawdown_pct": drawdown["maximum_drawdown_pct"],
            "r_multiple": sum(float(calculate_r_multiple(t)) for t in trades if isinstance(calculate_r_multiple(t), (int, float))),
        },
        "equity_curve": [round(value, 2) for value in equity_curve],
        "trades": [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "side": trade.side,
                "net_profit": trade.net_profit,
                "strategy_id": trade.strategy_id,
                "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                "r_multiple": calculate_r_multiple(trade),
            }
            for trade in sorted(trades, key=lambda t: t.entry_time or datetime.utcnow(), reverse=True)
        ],
    }
    return dashboard


@app.get("/api/analytics/summary")
def analytics_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    account = ensure_demo_account(db, current_user.id)
    trades = db.query(Trade).filter(Trade.account_id == account.id).all()
    if not trades:
        trades = create_demo_trades(db, account.id)

    metrics = calculate_trade_metrics([trade.__dict__ for trade in trades])
    equity_curve = [float(account.initial_balance)]
    running_total = float(account.initial_balance)
    for trade in trades:
        running_total += float(trade.net_profit or 0.0)
        equity_curve.append(running_total)

    return {
        "metrics": metrics,
        "drawdown": calculate_drawdown(equity_curve),
        "equity_curve": equity_curve,
        "account_value": float(account.current_balance or account.initial_balance),
    }


@app.get("/api/analytics/strategies")
def strategy_analytics(
    account_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = db.query(Trade).join(Account).filter(Account.user_id == current_user.id)
    if account_id is not None:
        query = query.filter(Trade.account_id == account_id)
    trades = query.all()
    return {"strategies": calculate_strategy_metrics(trades)}


@app.get("/api/analytics/analyst")
def analyst_summary(
    account_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if account_id is None:
        account = ensure_demo_account(db, current_user.id)
    else:
        account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

    trades = db.query(Trade).filter(Trade.account_id == account.id).all()
    rules = db.query(RiskRule).filter(RiskRule.account_id == account.id).first()
    initial_balance = (rules.initial_balance if rules and rules.initial_balance > 0 else account.initial_balance) or 0.0
    risk_assessment = evaluate_risk(trades, initial_balance, rules)
    return generate_analyst_report(trades, risk_assessment, account.currency)
