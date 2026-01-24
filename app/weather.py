import requests
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_weather_forecast():
    """
    Fetches 7-day weather forecast for local coordinates using National Weather Service (weather.gov).
    Returns a list of dicts: {'date': date_obj, 'high': int, 'low': int}
    """
    from flask import current_app

    LAT = current_app.config["WEATHER_LAT"]
    LON = current_app.config["WEATHER_LON"]
    
    # NWS requires a specific User-Agent
    headers = {
        "User-Agent": "MECWS-Volunteer-Operations/1.0 (contact@mecws.org)"
    }

    try:
        # Step 1: Get Grid Points (Metadata)
        points_url = f"https://api.weather.gov/points/{LAT},{LON}"
        response = requests.get(points_url, headers=headers, timeout=5)
        response.raise_for_status()
        points_data = response.json()
        
        forecast_url = points_data.get("properties", {}).get("forecast")
        if not forecast_url:
            logger.error("NWS: No forecast URL found in points data.")
            return []

        # Step 2: Get Forecast
        response = requests.get(forecast_url, headers=headers, timeout=5)
        response.raise_for_status()
        forecast_data = response.json()
        
        periods = forecast_data.get("properties", {}).get("periods", [])
        
        # Process NWS periods into daily structure
        daily_weather = {}
        
        for p in periods:
            # parsed start time usually iso formatted: 2023-12-25T18:00:00-05:00
            start_time_str = p.get("startTime", "")
            if len(start_time_str) < 10:
                continue
                
            date_str = start_time_str[:10] # YYYY-MM-DD
            
            if date_str not in daily_weather:
                daily_weather[date_str] = {"high": None, "low": None}
            
            temp = p.get("temperature")
            is_daytime = p.get("isDaytime")
            
            if is_daytime:
                # Store high. If we somehow have multiple day periods for same date, take max.
                current_high = daily_weather[date_str]["high"]
                if current_high is None or temp > current_high:
                    daily_weather[date_str]["high"] = temp
            else:
                # Store low
                current_low = daily_weather[date_str]["low"]
                if current_low is None or temp < current_low:
                    daily_weather[date_str]["low"] = temp

        # Format output list
        forecast = []
        for d_str, data in daily_weather.items():
            try:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                
                # Fill missing values if NWS didn't provide one (e.g. night only forecast for today)
                # We interpret None as "No Data" but template expects number ideally.
                # However, template logic {{ day.weather.high }} might just show None.
                # Let's verify template: "day.weather.high" output directly. 
                # If None, it shows "None". 
                # Let's keep it None/raw so valid data is honest.
                
                forecast.append({
                    "date": d_obj,
                    "high": data["high"],
                    "low": data["low"]
                })
            except ValueError:
                continue
                
        # Sort by date
        forecast.sort(key=lambda x: x["date"])
        
        return forecast

    except Exception as e:
        logger.error(f"Error fetching weather from NWS: {e}")
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
