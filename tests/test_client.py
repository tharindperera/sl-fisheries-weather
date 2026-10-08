import pytest
import responses
import time
from sl_fisheries_weather.client.openmeteo import OpenMeteoClient

@responses.activate
def test_client_success():
    responses.add(responses.GET, "http://test.com", json={"success": True}, status=200)
    client = OpenMeteoClient()
    client.min_delay = 0
    res = client.fetch("http://test.com", {})
    assert res["success"] is True

@responses.activate
def test_client_429_retry(mocker):
    mocker.patch("time.sleep")
    responses.add(responses.GET, "http://test.com", json={"error": True}, status=429, headers={"Retry-After": "1"})
    responses.add(responses.GET, "http://test.com", json={"success": True}, status=200)
    
    client = OpenMeteoClient()
    client.min_delay = 0
    res = client.fetch("http://test.com", {})
    assert res["success"] is True
    assert len(responses.calls) == 2

@responses.activate
def test_client_500_exhaustion(mocker):
    mocker.patch("time.sleep")
    responses.add(responses.GET, "http://test.com", json={}, status=500)
    
    client = OpenMeteoClient()
    client.min_delay = 0
    with pytest.raises(RuntimeError, match="Failed to fetch"):
        client.fetch("http://test.com", {})
    assert len(responses.calls) == 5

@responses.activate
def test_client_json_decode_retry(mocker):
    mocker.patch("time.sleep")
    # First response returns invalid JSON (body empty or non-JSON), second returns valid JSON
    responses.add(responses.GET, "http://test.com", body="invalid json", status=200)
    responses.add(responses.GET, "http://test.com", json={"recovered": True}, status=200)
    
    client = OpenMeteoClient()
    client.min_delay = 0
    res = client.fetch("http://test.com", {})
    assert res["recovered"] is True
    assert len(responses.calls) == 2

@responses.activate
def test_client_400_bad_request():
    responses.add(responses.GET, "http://test.com", body="Bad request parameter", status=400)
    
    client = OpenMeteoClient()
    client.min_delay = 0
    with pytest.raises(RuntimeError, match="HTTP error"):
        client.fetch("http://test.com", {})
    # Must fail immediately without 5 retries
    assert len(responses.calls) == 1

@responses.activate
def test_client_429_long_retry_defer(mocker):
    from sl_fisheries_weather.budget.ledger import BudgetExceededError
    responses.add(responses.GET, "http://test.com", status=429, headers={"Retry-After": "3600"})
    
    client = OpenMeteoClient()
    client.min_delay = 0
    with pytest.raises(BudgetExceededError, match="Retry-After 3600s"):
        client.fetch("http://test.com", {})
