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
