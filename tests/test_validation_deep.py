import pytest
from sl_fisheries_weather.validation.checks import validate_response

def test_validate_response_missing_var():
    data = {"daily": {"time": ["2010-01-01"]}}
    with pytest.raises(ValueError, match="Missing variable temperature_2m_mean"):
        validate_response(data, 1, 1, "2010-01-01", ["temperature_2m_mean"])

def test_validate_response_null_interior():
    # Null interior, non-null tail should fail
    data = {"daily": {"time": ["2010-01-01", "2010-01-02", "2010-01-03"], "temperature_2m_mean": [25.0, None, 26.0]}}
    with pytest.raises(ValueError, match="Internal null detected"):
        validate_response(data, 1, 3, "2010-01-01", ["temperature_2m_mean"])

def test_validate_response_null_trailing():
    # Null trailing should pass (pending tail)
    data = {"daily": {"time": ["2010-01-01", "2010-01-02"], "temperature_2m_mean": [25.0, None]}}
    results = validate_response(data, 1, 2, "2010-01-01", ["temperature_2m_mean"])
    assert results[0]["daily"]["temperature_2m_mean"][1] is None

def test_validate_response_bounds():
    # Temperature bound
    data = {"daily": {"time": ["2010-01-01"], "temperature_2m_mean": [100.0]}}
    with pytest.raises(ValueError, match="out of bounds"):
        validate_response(data, 1, 1, "2010-01-01", ["temperature_2m_mean"])
    
    # Precipitation bound
    data = {"daily": {"time": ["2010-01-01"], "precipitation_sum": [-1.0]}}
    with pytest.raises(ValueError, match="cannot be negative"):
        validate_response(data, 1, 1, "2010-01-01", ["precipitation_sum"])

def test_validate_response_wrong_dates():
    data = {"daily": {"time": ["2010-01-02"], "temperature_2m_mean": [25.0]}}
    with pytest.raises(ValueError, match="Date sequence mismatch"):
        validate_response(data, 1, 1, "2010-01-01", ["temperature_2m_mean"])

def test_validate_response_wrong_units():
    data = {"daily": {"time": ["2010-01-01"], "temperature_2m_mean": [25.0]}, "daily_units": {"temperature_2m_mean": "F"}}
    with pytest.raises(ValueError, match="Unit mismatch"):
        validate_response(data, 1, 1, "2010-01-01", ["temperature_2m_mean"], {"temperature_2m_mean": "celsius"})
