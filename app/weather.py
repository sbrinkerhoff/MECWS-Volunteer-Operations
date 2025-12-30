import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_weather_forecast():
    """
    Fetches 14-day weather forecast for Montpelier, VT (05602).
    Returns a list of dicts: {'date': date_obj, 'high': int, 'low': int}
    """
    from flask import current_app

    # Montpelier, VT specific coordinates
    LAT = current_app.config["WEATHER_LAT"]
    LON = current_app.config["WEATHER_LON"]

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT,
            "longitude": LON,
            "daily": ["temperature_2m_max", "temperature_2m_min"],
            "temperature_unit": "fahrenheit",
            "timezone": "America/New_York",
            "forecast_days": 14,
        }

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])

        forecast = []
        for i, date_str in enumerate(dates):
            forecast.append(
                {
                    "date": datetime.strptime(date_str, "%Y-%m-%d").date(),
                    "high": round(highs[i]),
                    "low": round(lows[i]),
                }
            )

        return forecast

    except Exception as e:
        logger.error(f"Error fetching weather: {e}")
        return []


def get_weather_calendar():
    """
    Returns a list of weeks, where each week is a list of days.
    Each day is {'date': date, 'weather': dict|None, 'is_today': bool, 'is_past': bool}
    Covers the current week (starting Sunday) and the next week.
    """
    forecast = get_weather_forecast()
    forecast_map = {d["date"]: d for d in forecast} if forecast else {}

    today = datetime.now().date()
    # Find start of the calendar (last Sunday)
    # weekday(): Mon=0 ... Sun=6
    # If today is Sun(6), we start today. shift=0.
    # If today is Mon(0), we start yesterday. shift=1.
    days_since_sunday = (today.weekday() + 1) % 7
    start_date = today - timedelta(days=days_since_sunday)

    weeks = []
    current_week = []

    # Generate 2 weeks (14 days)
    for i in range(14):
        date_obj = start_date + timedelta(days=i)

        weather_data = forecast_map.get(date_obj)

        day_info = {
            "date": date_obj,
            "day_name": date_obj.strftime("%a"),  # Sun, Mon...
            "weather": weather_data,
            "is_today": date_obj == today,
            "is_past": date_obj < today,
        }

        current_week.append(day_info)

        if len(current_week) == 7:
            weeks.append(current_week)
            current_week = []

    return weeks
