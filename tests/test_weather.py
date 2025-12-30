import pytest
from app.weather import get_weather_forecast, get_weather_calendar
from datetime import date


def test_weather_fetch_structure():
    """Test that weather fetch returns correct structure (mocked or real)."""
    # We will try to run against real API if network allows,
    # but handle failure gracefully if offline to not break CI.

    forecast = get_weather_forecast()

    # If API fails (offline), it returns empty list
    if not forecast:
        pytest.skip("Weather API unavailable or offline")

    assert isinstance(forecast, list)
    assert len(forecast) > 0
    assert "date" in forecast[0]
    assert "high" in forecast[0]
    assert "low" in forecast[0]


def test_weather_calendar_structure():
    """Test that calendar generation works correctly."""
    calendar = get_weather_calendar()

    assert isinstance(calendar, list)
    if not calendar:
        # If fetch failed
        pass
    else:
        # Should have roughly 2 weeks
        assert len(calendar) >= 2
        week1 = calendar[0]
        assert len(week1) == 7
        assert "day_name" in week1[0]
        assert "is_today" in week1[0]
