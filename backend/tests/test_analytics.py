from backend.app.services.analytics import (
    calculate_drawdown,
    calculate_strategy_metrics,
    calculate_trade_metrics,
    calculate_r_multiple,
)


def test_calculate_trade_metrics():
    trades = [
        {"net_profit": 100.0, "risk_amount": 50.0},
        {"net_profit": -40.0, "risk_amount": 50.0},
        {"net_profit": 80.0, "risk_amount": 40.0},
        {"net_profit": -30.0, "risk_amount": 30.0},
        {"net_profit": 60.0, "risk_amount": 30.0},
    ]

    metrics = calculate_trade_metrics(trades)

    assert metrics["total_trades"] == 5
    assert metrics["winning_trades"] == 3
    assert metrics["losing_trades"] == 2
    assert metrics["win_rate"] == 0.6
    assert metrics["gross_profit"] == 240.0
    assert metrics["gross_loss"] == 70.0
    assert metrics["net_profit"] == 170.0
    assert metrics["average_win"] == 80.0
    assert metrics["average_loss"] == 35.0
    assert metrics["profit_factor"] == 3.4285714285714284
    assert metrics["expectancy"] == 34.0


def test_calculate_r_multiple_with_valid_risk():
    trade = {"net_profit": 120.0, "risk_amount": 40.0}

    assert calculate_r_multiple(trade) == 3.0


def test_calculate_r_multiple_without_risk_returns_na():
    trade = {"net_profit": 120.0}

    assert calculate_r_multiple(trade) == "N/A"


def test_calculate_drawdown():
    equity_curve = [1000, 1100, 950, 900, 1200, 1100]

    summary = calculate_drawdown(equity_curve)

    assert summary["peak_equity"] == 1200
    assert summary["maximum_drawdown"] == 300
    assert summary["maximum_drawdown_pct"] == 0.25
    assert summary["current_drawdown"] == 100
    assert summary["current_drawdown_pct"] == 0.08333333333333333


def test_calculate_strategy_metrics_groups_and_sorts_by_net_profit():
    trades = [
        {"strategy_id": "Breakout", "net_profit": 100.0},
        {"strategy_id": "Reversal", "net_profit": -20.0},
        {"strategy_id": "Breakout", "net_profit": -30.0},
    ]

    results = calculate_strategy_metrics(trades)

    assert results[0]["strategy_id"] == "Breakout"
    assert results[0]["total_trades"] == 2
    assert results[0]["net_profit"] == 70.0
    assert results[1]["strategy_id"] == "Reversal"
    assert results[1]["net_profit"] == -20.0
