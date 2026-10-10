from datetime import date, datetime, timezone

from backend.app.services.risk import evaluate_risk


def test_evaluate_risk_detects_daily_and_total_loss_breaches():
    trades = [
        {"net_profit": -120.0, "entry_time": datetime(2026, 9, 30, 10, tzinfo=timezone.utc)},
        {"net_profit": -80.0, "entry_time": datetime(2026, 9, 29, 10, tzinfo=timezone.utc)},
    ]
    rules = {"daily_loss_limit": 100.0, "max_loss": 150.0, "max_drawdown": 0.0, "profit_target": 0.0}

    result = evaluate_risk(trades, 10000.0, rules, as_of=date(2026, 9, 30))

    assert result["status"] == "breached"
    assert result["daily_net_profit"] == -120.0
    assert result["total_net_profit"] == -200.0
    assert {check["key"] for check in result["checks"] if check["status"] == "breached"} == {"daily_loss", "max_loss"}


def test_evaluate_risk_disables_zero_limits_and_tracks_profit_target():
    trades = [{"net_profit": 250.0, "entry_time": datetime(2026, 9, 30, 10, tzinfo=timezone.utc)}]
    rules = {"daily_loss_limit": 0.0, "max_loss": 0.0, "max_drawdown": 0.0, "profit_target": 200.0}

    result = evaluate_risk(trades, 10000.0, rules, as_of=date(2026, 9, 30))

    assert result["status"] == "on_track"
    assert result["current_balance"] == 10250.0
    assert next(check for check in result["checks"] if check["key"] == "profit_target")["status"] == "met"
    assert all(check["status"] == "disabled" for check in result["checks"][:3])


def test_evaluate_risk_detects_peak_to_trough_drawdown():
    trades = [
        {"net_profit": 500.0, "entry_time": datetime(2026, 9, 29, 10, tzinfo=timezone.utc)},
        {"net_profit": -300.0, "entry_time": datetime(2026, 9, 30, 10, tzinfo=timezone.utc)},
    ]
    rules = {"daily_loss_limit": 0.0, "max_loss": 0.0, "max_drawdown": 250.0, "profit_target": 0.0}

    result = evaluate_risk(trades, 10000.0, rules, as_of=date(2026, 9, 30))

    drawdown_check = next(check for check in result["checks"] if check["key"] == "max_drawdown")
    assert result["maximum_drawdown"] == 300.0
    assert drawdown_check["status"] == "breached"


def test_evaluate_risk_checks_trading_days_consistency_and_position_size():
    trades = [
        {"net_profit": 300.0, "volume": 1.0, "entry_time": datetime(2026, 9, 28, 10, tzinfo=timezone.utc)},
        {"net_profit": 100.0, "volume": 0.5, "entry_time": datetime(2026, 9, 29, 10, tzinfo=timezone.utc)},
    ]
    rules = {
        "minimum_trading_days": 3,
        "consistency_requirement": 60.0,
        "position_size_limit": 0.75,
    }

    result = evaluate_risk(trades, 10000.0, rules, as_of=date(2026, 9, 30))
    checks = {check["key"]: check for check in result["checks"]}

    assert checks["minimum_trading_days"]["status"] == "in_progress"
    assert checks["consistency"]["actual"] == 75.0
    assert checks["consistency"]["status"] == "breached"
    assert checks["position_size"]["actual"] == 1.0
    assert checks["position_size"]["status"] == "breached"
    assert result["status"] == "breached"


def test_evaluate_risk_marks_news_and_missing_weekend_data_not_evaluable():
    trades = [{"net_profit": 10.0, "volume": 0.1, "entry_time": datetime(2026, 9, 28, 10, tzinfo=timezone.utc)}]
    rules = {"news_restriction": True, "weekend_restriction": True}

    result = evaluate_risk(trades, 10000.0, rules, as_of=date(2026, 9, 30))
    checks = {check["key"]: check for check in result["checks"]}

    assert checks["news_restriction"]["status"] == "not_evaluable"
    assert checks["weekend_restriction"]["status"] == "not_evaluable"
    assert result["status"] == "review_required"


def test_evaluate_risk_detects_trades_held_across_weekend():
    trades = [{
        "net_profit": 25.0,
        "entry_time": datetime(2026, 9, 25, 15, tzinfo=timezone.utc),
        "exit_time": datetime(2026, 9, 28, 9, tzinfo=timezone.utc),
    }]
    rules = {"weekend_restriction": True}

    result = evaluate_risk(trades, 10000.0, rules, as_of=date(2026, 9, 30))

    assert next(check for check in result["checks"] if check["key"] == "weekend_restriction")["status"] == "breached"


def test_evaluate_risk_detects_news_event_overlap_when_calendar_is_present():
    trades = [{
        "symbol": "EURUSD",
        "net_profit": 25.0,
        "entry_time": datetime(2026, 9, 30, 8, 45, tzinfo=timezone.utc),
        "exit_time": datetime(2026, 9, 30, 9, 15, tzinfo=timezone.utc),
    }]
    rules = {
        "news_restriction": True,
        "news_events": [{
            "symbol": "EURUSD",
            "time": "2026-09-30T08:30:00Z",
            "impact": "high",
        }],
    }

    result = evaluate_risk(trades, 10000.0, rules, as_of=date(2026, 9, 30))

    assert next(check for check in result["checks"] if check["key"] == "news_restriction")["status"] == "breached"


def test_evaluate_risk_allows_position_size_at_exact_limit():
    trades = [{"net_profit": 10.0, "volume": 1.0}]

    result = evaluate_risk(trades, 10000.0, {"position_size_limit": 1.0})

    position_check = next(check for check in result["checks"] if check["key"] == "position_size")
    assert position_check["status"] == "within_limit"