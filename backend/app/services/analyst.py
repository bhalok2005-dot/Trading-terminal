from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable

from .analytics import calculate_strategy_metrics, calculate_trade_metrics


def generate_analyst_report(
    trades: Iterable[Any],
    risk_assessment: dict[str, Any],
    currency: str = "USD",
) -> dict[str, Any]:
    trade_list = list(trades)
    metrics = calculate_trade_metrics(trade_list)
    strategies = calculate_strategy_metrics(trade_list)
    trade_count = int(metrics["total_trades"])
    confidence = "none" if trade_count == 0 else "low" if trade_count < 10 else "moderate" if trade_count < 30 else "higher"

    if trade_count == 0:
        summary = "No closed trades are available for analysis."
        insights = [{
            "key": "no_data",
            "severity": "neutral",
            "title": "Waiting for trade history",
            "detail": "Import closed trades to establish a performance baseline.",
        }]
    else:
        net_profit = float(metrics["net_profit"])
        expectancy = float(metrics["expectancy"])
        summary = (
            f"Across {trade_count} closed trades, net P&L is {currency} {net_profit:,.2f} "
            f"with expectancy {currency} {expectancy:,.2f} per trade."
        )
        insights: list[dict[str, str]] = []

        if trade_count < 10:
            insights.append({
                "key": "sample_size",
                "severity": "caution",
                "title": "Limited sample",
                "detail": f"{trade_count} trades are not enough to treat this performance pattern as stable.",
            })

        if risk_assessment.get("status") == "breached":
            breached = [check["label"] for check in risk_assessment.get("checks", []) if check.get("status") == "breached"]
            insights.append({
                "key": "risk_breach",
                "severity": "critical",
                "title": "Risk limit breached",
                "detail": f"Current history exceeds: {', '.join(breached)}.",
            })

        if expectancy > 0:
            insights.append({
                "key": "positive_expectancy",
                "severity": "positive",
                "title": "Positive expectancy",
                "detail": f"Average outcome is {currency} {expectancy:,.2f} per trade across this sample.",
            })
        elif expectancy < 0:
            insights.append({
                "key": "negative_expectancy",
                "severity": "warning",
                "title": "Negative expectancy",
                "detail": f"Average outcome is {currency} {expectancy:,.2f} per trade; review execution and trade selection.",
            })

        average_win = float(metrics["average_win"])
        average_loss = float(metrics["average_loss"])
        if average_win > 0 and average_loss > average_win * 1.25:
            insights.append({
                "key": "loss_size",
                "severity": "caution",
                "title": "Losses outweigh wins",
                "detail": f"Average loss ({currency} {average_loss:,.2f}) is more than 25% larger than average win ({currency} {average_win:,.2f}).",
            })

        if strategies and strategies[0]["total_trades"] >= 3 and strategies[0]["net_profit"] > 0:
            strongest = strategies[0]
            insights.append({
                "key": "leading_strategy",
                "severity": "positive",
                "title": f"Leading strategy: {strongest['strategy_id']}",
                "detail": f"It has {strongest['total_trades']} trades and net P&L of {currency} {strongest['net_profit']:,.2f}.",
            })

        if not insights:
            insights.append({
                "key": "steady",
                "severity": "neutral",
                "title": "No dominant pattern detected",
                "detail": "Current metrics do not cross the analyst's review thresholds.",
            })

    profit_factor = float(metrics["profit_factor"])
    return {
        "method": "rules_based",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confidence": confidence,
        "summary": summary,
        "metrics": {
            "total_trades": trade_count,
            "win_rate": round(float(metrics["win_rate"]), 4),
            "net_profit": round(float(metrics["net_profit"]), 2),
            "expectancy": round(float(metrics["expectancy"]), 2),
            "profit_factor": round(profit_factor, 2) if math.isfinite(profit_factor) else None,
        },
        "risk_status": risk_assessment.get("status", "unknown"),
        "insights": insights,
        "disclaimer": "Performance summaries describe historical trades and do not predict future results.",
    }