from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    broker = Column(String(255), default="Demo")
    prop_firm = Column(String(255), nullable=True)
    account_number = Column(String(100), nullable=True)
    initial_balance = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    currency = Column(String(10), default="USD")
    account_type = Column(String(50), default="demo")
    status = Column(String(50), default="active")
    connection_type = Column(String(50), default="csv")
    broker_config = Column(String(5000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="accounts")
    trades = relationship("Trade", back_populates="account", cascade="all, delete-orphan")
    risk_rules = relationship("RiskRule", back_populates="account", cascade="all, delete-orphan")


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (UniqueConstraint("account_id", "external_trade_id", name="uq_trade_account_external"),)

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    external_trade_id = Column(String(100), nullable=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(20), nullable=False, default="long")
    volume = Column(Float, default=0.0)
    entry_price = Column(Float, default=0.0)
    exit_price = Column(Float, default=0.0)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    entry_time = Column(DateTime(timezone=True), nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    profit = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    risk_amount = Column(Float, nullable=True)
    r_multiple = Column(Float, nullable=True)
    strategy_id = Column(String(50), default="Manual")
    session = Column(String(50), default="London")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    account = relationship("Account", back_populates="trades")


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    initial_balance = Column(Float, default=0.0)
    profit_target = Column(Float, default=0.0)
    daily_loss_limit = Column(Float, default=0.0)
    max_loss = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    minimum_trading_days = Column(Integer, default=0)
    consistency_requirement = Column(Float, default=0.0)
    position_size_limit = Column(Float, default=0.0)
    news_restriction = Column(Boolean, default=False)
    weekend_restriction = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    account = relationship("Account", back_populates="risk_rules")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    trades_fetched = Column(Integer, default=0)
    inserted = Column(Integer, default=0)
    updated = Column(Integer, default=0)
    errors = Column(String(500), nullable=True)
    status = Column(String(50), default="success")

    account = relationship("Account")
