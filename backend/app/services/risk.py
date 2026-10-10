from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from .news import NewsCalendar


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _as_utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _trade_time(trade: Any) -> datetime | None:
    return _as_utc(_value(trade, "exit_time")) or _as_utc(_value(trade, "entry_time"))


def evaluate_risk(
    trades: Iterable[Any],
    initial_balance: float,
    rules: Any,
    as_of: date | None = None,
) -> dict[str, Any]:
    trade_list = list(trades)
    today = as_of or datetime.now(timezone.utc).date()
    ordered_trades = sorted(trade_list, key=lambda trade: _trade_time(trade) or datetime.min.replace(tzinfo=timezone.utc))
    profits = [float(_value(trade, "net_profit", 0.0) or 0.0) for trade in ordered_trades]
    daily_profits: dict[date, float] = {}
    trading_days: set[date] = set()
    for trade, profit in zip(ordered_trades, profits):
        trade_time = _trade_time(trade)
        if trade_time is not None:
            trade_day = trade_time.date()
            trading_days.add(trade_day)
            daily_profits[trade_day] = daily_profits.get(trade_day, 0.0) + profit
    daily_profit = daily_profits.get(today, 0.0)
    total_profit = sum(profits)

    equity = float(initial_balance)
    peak = equity
    maximum_drawdown = 0.0
    for profit in profits:
        equity += profit
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, peak - equity)

    checks: list[dict[str, Any]] = []

    def add_limit_check(key: str, label: str, actual: float, limit: float, breach_on_equal: bool = True) -> None:
        if limit <= 0:
            checks.append({"key": key, "label": label, "status": "disabled", "actual": actual, "limit": limit})
        else:
            breached = actual >= limit if breach_on_equal else actual > limit
            checks.append({
                "key": key,
                "label": label,
                "status": "breached" if breached else "within_limit",
                "actual": round(actual, 2),
                "limit": limit,
            })

    add_limit_check("daily_loss", "Daily loss", max(0.0, -daily_profit), float(_value(rules, "daily_loss_limit", 0.0) or 0.0))
    add_limit_check("max_loss", "Total loss", max(0.0, -total_profit), float(_value(rules, "max_loss", 0.0) or 0.0))
    add_limit_check("max_drawdown", "Maximum drawdown", maximum_drawdown, float(_value(rules, "max_drawdown", 0.0) or 0.0))

    minimum_trading_days = int(_value(rules, "minimum_trading_days", 0) or 0)
    has_undated_trades = any(_trade_time(trade) is None for trade in trade_list)
    if minimum_trading_days <= 0:
        checks.append({"key": "minimum_trading_days", "label": "Minimum trading days", "status": "disabled", "actual": len(trading_days), "limit": minimum_trading_days})
    elif len(trading_days) >= minimum_trading_days:
        checks.append({"key": "minimum_trading_days", "label": "Minimum trading days", "status": "met", "actual": len(trading_days), "limit": minimum_trading_days})
    else:
        checks.append({
            "key": "minimum_trading_days",
            "label": "Minimum trading days",
            "status": "not_evaluable" if has_undated_trades else "in_progress",
            "actual": len(trading_days),
            "limit": minimum_trading_days,
            "detail": "Some trades have no usable timestamp." if has_undated_trades else "Trading days are still accumulating.",
        })

    consistency_limit = float(_value(rules, "consistency_requirement", 0.0) or 0.0)
    positive_day_profits = [profit for profit in daily_profits.values() if profit > 0]
    if consistency_limit <= 0:
        checks.append({"key": "consistency", "label": "Best-day profit share", "status": "disabled", "actual": 0.0, "limit": consistency_limit})
    elif not positive_day_profits:
        checks.append({
            "key": "consistency",
            "label": "Best-day profit share",
            "status": "not_evaluable",
            "actual": 0.0,
            "limit": consistency_limit,
            "detail": "No positive trading-day profit is available to measure.",
        })
    else:
        positive_profit_total = sum(positive_day_profits)
        best_day_share = max(positive_day_profits) / positive_profit_total * 100
        checks.append({
            "key": "consistency",
            "label": "Best-day profit share",
            "status": "breached" if best_day_share > consistency_limit else "within_limit",
            "actual": round(best_day_share, 2),
            "limit": consistency_limit,
        })

    position_size_limit = float(_value(rules, "position_size_limit", 0.0) or 0.0)
    maximum_position_size = max((float(_value(trade, "volume", 0.0) or 0.0) for trade in trade_list), default=0.0)
    add_limit_check("position_size", "Position size", maximum_position_size, position_size_limit, breach_on_equal=False)

    if not bool(_value(rules, "news_restriction", False)):
        checks.append({"key": "news_restriction", "label": "News restriction", "status": "disabled"})
    else:
        news_events = _value(rules, "news_events", None)
        if news_events is None:
            news_events = _value(rules, "news_calendar", None)
        if news_events is None:
            news_events = _value(rules, "events", None)
        if news_events is None:
            news_events = NewsCalendar.from_env().events

        if not news_events:
            checks.append({
                "key": "news_restriction",
                "label": "News restriction",
                "status": "not_evaluable",
                "detail": "No news-event calendar is connected to verify restricted trading windows.",
            })
        else:
            calendar = NewsCalendar.from_config(news_events)
            trade_overlap = False
            for trade in trade_list:
                symbol = str(_value(trade, "symbol", "") or "").upper() or None
                entry_time = _as_utc(_value(trade, "entry_time"))
                exit_time = _as_utc(_value(trade, "exit_time"))
                if calendar.has_trade_overlap(symbol, entry_time, exit_time):
                    trade_overlap = True
                    break
            checks.append({
                "key": "news_restriction",
                "label": "News restriction",
                "status": "breached" if trade_overlap else "within_limit",
                "detail": "High-impact news overlapped a trade window." if trade_overlap else "No high-impact news event overlapped the trade window.",
            })

    weekend_restriction = bool(_value(rules, "weekend_restriction", False))
    if not weekend_restriction:
        checks.append({"key": "weekend_restriction", "label": "Weekend restriction", "status": "disabled"})
    else:
        weekend_trade_found = False
        incomplete_weekend_data = False
        for trade in trade_list:
            entry_time = _as_utc(_value(trade, "entry_time"))
            exit_time = _as_utc(_value(trade, "exit_time"))
            if entry_time is None or exit_time is None or exit_time < entry_time:
                incomplete_weekend_data = True
                continue
            current_day = entry_time.date()
            while current_day <= exit_time.date():
                if current_day.weekday() >= 5:
                    weekend_trade_found = True
                    break
                current_day += timedelta(days=1)
            if weekend_trade_found:
                break

        if weekend_trade_found:
            checks.append({"key": "weekend_restriction", "label": "Weekend restriction", "status": "breached"})
        elif incomplete_weekend_data:
            checks.append({
                "key": "weekend_restriction",
                "label": "Weekend restriction",
                "status": "not_evaluable",
                "detail": "Entry and exit timestamps are required to verify weekend exposure.",
            })
        else:
            checks.append({"key": "weekend_restriction", "label": "Weekend restriction", "status": "within_limit"})

    profit_target = float(_value(rules, "profit_target", 0.0) or 0.0)
    checks.append({
        "key": "profit_target",
        "label": "Profit target",
        "status": "disabled" if profit_target <= 0 else "met" if total_profit >= profit_target else "in_progress",
        "actual": round(total_profit, 2),
        "target": profit_target,
    })

    overall_status = (
        "breached" if any(check["status"] == "breached" for check in checks)
        else "review_required" if any(check["status"] == "not_evaluable" for check in checks)
        else "on_track"
    )

    return {
        "status": overall_status,
        "as_of": today.isoformat(),
        "trade_count": len(trade_list),
        "daily_net_profit": round(daily_profit, 2),
        "total_net_profit": round(total_profit, 2),
        "current_balance": round(float(initial_balance) + total_profit, 2),
        "maximum_drawdown": round(maximum_drawdown, 2),
        "checks": checks,
    }