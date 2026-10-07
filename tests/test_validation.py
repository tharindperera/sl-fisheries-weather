import pytest
from sl_fisheries_weather.validation.checks import validate_response

def test_validate_response_valid():
    data = [{
        "latitude": 7.0, "longitude": 79.8,
        "daily": {"time": ["2010-01-01"], "precipitation_sum": [0.0]}
    }]
    results = validate_response(data, 1, 1, "2010-01-01", ["precipitation_sum"])
    assert len(results) == 1

def test_validate_response_error():
    data = {"error": True, "reason": "rate limit"}
    with pytest.raises(ValueError, match="API Error"):
        validate_response(data, 1, 1, "2010-01-01", [])

def test_validate_response_wrong_locations():
    data = [{"daily": {"time": ["2010-01-01"]}}]
    with pytest.raises(ValueError, match="Expected 2 locations"):
        validate_response(data, 2, 1, "2010-01-01", [])

def test_validate_response_wrong_days():
    data = [{"daily": {"time": ["2010-01-01", "2010-01-02"]}}]
    # Now this just returns the available days up to expected if smaller
    results = validate_response(data, 1, 1, "2010-01-01", [])
    assert len(results[0]["daily"]["time"]) == 2
        
def test_validate_response_mismatch_arrays():
    data = [{"daily": {"time": ["2010-01-01"], "precipitation_sum": []}}]
    # This should now result in an empty valid prefix
    results = validate_response(data, 1, 1, "2010-01-01", ["precipitation_sum"])
    assert len(results[0]["daily"]["time"]) == 0
