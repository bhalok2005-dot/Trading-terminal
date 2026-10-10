from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    is_active: bool = True

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountCreate(BaseModel):
    name: str
    broker: str = "Demo"
    prop_firm: Optional[str] = None
    account_number: Optional[str] = None
    initial_balance: float = 0.0
    current_balance: float = 0.0
    currency: str = "USD"
    account_type: str = "demo"
    status: str = "active"
    connection_type: str = "csv"
    broker_config: Optional[str] = None


class AccountRead(AccountCreate):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TradeBase(BaseModel):
    account_id: int
    external_trade_id: Optional[str] = None
    symbol: str
    side: str = "long"
    volume: float = 0.0
    entry_price: float = 0.0
    exit_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    profit: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    net_profit: float = 0.0
    risk_amount: Optional[float] = None
    r_multiple: Optional[float] = None
    strategy_id: str = "Manual"
    session: str = "London"


class TradeCreate(TradeBase):
    pass


class TradeRead(TradeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RiskRuleUpsert(BaseModel):
    initial_balance: float = Field(default=0.0, ge=0)
    profit_target: float = Field(default=0.0, ge=0)
    daily_loss_limit: float = Field(default=0.0, ge=0)
    max_loss: float = Field(default=0.0, ge=0)
    max_drawdown: float = Field(default=0.0, ge=0)
    minimum_trading_days: int = Field(default=0, ge=0)
    consistency_requirement: float = Field(default=0.0, ge=0, le=100)
    position_size_limit: float = Field(default=0.0, ge=0)
    news_restriction: bool = False
    weekend_restriction: bool = False


class RiskRuleRead(RiskRuleUpsert):
    id: int
    account_id: int

    class Config:
        from_attributes = True


class SyncLogRead(BaseModel):
    id: int
    account_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    trades_fetched: int
    inserted: int
    updated: int
    errors: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class DashboardSummary(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    net_profit: float
    average_win: float
    average_loss: float
    profit_factor: float
    expectancy: float
    max_drawdown: float
    max_drawdown_pct: float
    balance: float
    equity: float
    daily_pnl: float
