from __future__ import annotations

import math
from typing import Any, Iterable, Sequence


def _value(item: Any, key: str, default: float = 0.0) -> float:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def calculate_trade_metrics(trades: Sequence[Any] | Iterable[Any]) -> dict[str, float | int]:
    trade_list = list(trades)
    if not trade_list:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_profit": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
        }

    profits = [float(_value(trade, "net_profit", 0.0)) for trade in trade_list]
    wins = [p for p in profits if p > 0]
    losses = [abs(p) for p in profits if p < 0]

    total = len(profits)
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    net_profit = sum(profits)
    win_rate = len(wins) / total if total else 0.0
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = 0.0 if gross_profit == 0 else float("inf")

    expectancy = (win_rate * average_win) - ((1 - win_rate) * average_loss)

    return {
        "total_trades": total,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_profit": net_profit,
        "average_win": average_win,
        "average_loss": average_loss,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
    }


def calculate_strategy_metrics(trades: Iterable[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = {}
    for trade in trades:
        strategy_id = str(_value(trade, "strategy_id", "Manual") or "Manual")
        grouped.setdefault(strategy_id, []).append(trade)

    results = [
        {"strategy_id": strategy_id, **calculate_trade_metrics(strategy_trades)}
        for strategy_id, strategy_trades in grouped.items()
    ]
    return sorted(results, key=lambda result: result["net_profit"], reverse=True)


def calculate_r_multiple(trade: dict[str, Any] | Any) -> float | str:
    risk_amount = float(_value(trade, "risk_amount", 0.0))
    net_profit = float(_value(trade, "net_profit", 0.0))

    if risk_amount is None or risk_amount == 0:
        return "N/A"

    if not math.isfinite(risk_amount):
        return "N/A"

    return net_profit / risk_amount


def calculate_drawdown(equity_curve: Sequence[float]) -> dict[str, float]:
    if not equity_curve:
        return {
            "peak_equity": 0.0,
            "current_drawdown": 0.0,
            "maximum_drawdown": 0.0,
            "maximum_drawdown_pct": 0.0,
            "current_drawdown_pct": 0.0,
        }

    peak_equity = max(float(value) for value in equity_curve)
    current_equity = float(equity_curve[-1])
    trough_equity = min(float(value) for value in equity_curve)
    max_drawdown = max(0.0, peak_equity - trough_equity)

    current_drawdown = max(0.0, peak_equity - current_equity)
    max_drawdown_pct = (max_drawdown / peak_equity) if peak_equity else 0.0
    current_drawdown_pct = (current_drawdown / peak_equity) if peak_equity else 0.0

    return {
        "peak_equity": peak_equity,
        "current_drawdown": current_drawdown,
        "maximum_drawdown": max_drawdown,
        "maximum_drawdown_pct": max_drawdown_pct,
        "current_drawdown_pct": current_drawdown_pct,
    }
