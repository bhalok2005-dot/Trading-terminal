from backend.app.services.analyst import generate_analyst_report


def test_analyst_report_flags_small_sample_and_risk_breach():
    trades = [{"net_profit": 25.0, "strategy_id": "Breakout"} for _ in range(5)]
    risk_assessment = {
        "status": "breached",
        "checks": [{"label": "Daily loss", "status": "breached"}],
    }

    report = generate_analyst_report(trades, risk_assessment)

    assert report["method"] == "rules_based"
    assert report["confidence"] == "low"
    assert report["metrics"]["net_profit"] == 125.0
    assert {insight["key"] for insight in report["insights"]} >= {"sample_size", "risk_breach"}


def test_analyst_report_handles_no_trades_without_non_finite_values():
    report = generate_analyst_report([], {"status": "on_track", "checks": []})

    assert report["confidence"] == "none"
    assert report["metrics"]["profit_factor"] == 0.0
    assert report["insights"][0]["key"] == "no_data"