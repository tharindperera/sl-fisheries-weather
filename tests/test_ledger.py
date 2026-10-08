import pytest
from sl_fisheries_weather.budget.ledger import Ledger, BudgetExceededError

def test_ledger_rolling_window(mocker):
    ledger = Ledger({"minute": 100, "hour": 1000, "day": 5000, "month": 15000})
    ledger.state = {
        "minute_calls": [],
        "hour_calls": [],
        "day_calls": [],
        "month_calls": []
    }
    
    # Mock time
    mocker.patch("sl_fisheries_weather.budget.ledger.Ledger._now", return_value=100.0)
    
    # Consume 90
    ledger.reserve(90)
    assert ledger.can_consume(10) is True
    assert ledger.can_consume(20) is False
    
    with pytest.raises(BudgetExceededError):
        ledger.reserve(20)
        
    # Advance time by 61 seconds
    mocker.patch("sl_fisheries_weather.budget.ledger.Ledger._now", return_value=161.0)
    
    # Old calls should expire from minute_calls
    assert ledger.can_consume(20) is True
    ledger.reserve(20)
    
    # Total in hour is now 90 + 20 = 110. Let's assert it is 110.
    ledger._cleanup_rolling()
    assert ledger._get_sum("hour_calls") == 110
    
    # Test refund
    ledger.refund(10)
    ledger._cleanup_rolling()
    assert ledger._get_sum("minute_calls") == 10

def test_ledger_wait_for_minute_capacity(mocker):
    ledger = Ledger({"minute": 100, "hour": 1000, "day": 5000, "month": 15000})
    mocker.patch("time.sleep")
    times = [100.0, 100.0, 161.0, 161.0]
    mocker.patch("sl_fisheries_weather.budget.ledger.Ledger._now", side_effect=lambda: times.pop(0) if times else 200.0)
    
    ledger.state = {
        "minute_calls": [{"time": 100.0, "cost": 90}],
        "hour_calls": [{"time": 100.0, "cost": 90}],
        "day_calls": [{"time": 100.0, "cost": 90}],
        "month_calls": [{"time": 100.0, "cost": 90}]
    }
    
    # Should wait and return True once time advances past 60s
    assert ledger.wait_for_minute_capacity(20, max_wait=70.0) is True

def test_ledger_reload(tmp_path, mocker):
    mocker.patch("sl_fisheries_weather.budget.ledger.DATA_DIR", str(tmp_path))
    ledger = Ledger({"minute": 100, "hour": 1000, "day": 5000, "month": 15000})
    ledger.reserve(15)
    
    # Another instance loading same path
    ledger2 = Ledger({"minute": 100, "hour": 1000, "day": 5000, "month": 15000})
    assert ledger2._get_sum("minute_calls") == 15
    
    # Simulate external update and reload
    ledger.reserve(25)
    assert ledger2._get_sum("minute_calls") == 15
    ledger2.reload()
    assert ledger2._get_sum("minute_calls") == 40
