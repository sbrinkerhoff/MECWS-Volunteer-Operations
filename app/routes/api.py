
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Blueprint, jsonify, current_app, request
from app.models import Event

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/event/<date_str>')
@api_bp.route('/event/today')
def event_status(date_str="today"):
    target_date = None
    
    if date_str != "today":
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    if target_date is None:
        tz_name = current_app.config.get('TIMEZONE', 'America/New_York')
        now = datetime.now(ZoneInfo(tz_name))
        
        # If it's before 4AM, show yesterday's event (likely the active shelter night)
        if now.hour < 4:
            target_date = now.date() - timedelta(days=1)
        else:
            target_date = now.date()
        
    event = Event.query.filter_by(date=target_date).first()
    
    if event and event.status != 'cancelled':
        # Calculate volunteer status
        total_capacity = sum(s.capacity for s in event.shifts)
        total_confirmed = sum(s.confirmed_count for s in event.shifts)
        
        status_summary = {
            "date": event.date.isoformat(),
            "event_status": event.status,
            "volunteer_status": {
                "confirmed": total_confirmed,
                "capacity": total_capacity,
                "fully_staffed": total_confirmed >= total_capacity,
                "percentage": round(total_confirmed / total_capacity * 100) if total_capacity > 0 else 0
            },
            "shifts": [
                {
                    "id": s.id,
                    "start_time": s.start_time.strftime("%I:%M %p"),
                    "end_time": s.end_time.strftime("%I:%M %p"),
                    "confirmed": s.confirmed_count,
                    "capacity": s.capacity
                }
                for s in event.shifts
            ]
        }
        return jsonify(status_summary)
    
    return jsonify({"message": "No event found for today"}), 404


def get_season_dates(season_str):
    """
    Parses a season string (e.g. '2025-2026') and returns 
    the start and end dates for that season.
    Season runs from July 1st of the start year to June 30th of the end year.
    """
    try:
        start_year_str, end_year_str = season_str.split('-')
        start_year = int(start_year_str)
        end_year = int(end_year_str)
        
        if end_year != start_year + 1:
            return None, None
            
        start_date = datetime(start_year, 7, 1).date()
        end_date = datetime(end_year, 6, 30).date()
        
        return start_date, end_date
    except ValueError:
        return None, None


@api_bp.route('/season/<season_str>/summary')
def season_summary(season_str):
    start_date, end_date = get_season_dates(season_str)
    
    if not start_date:
        return jsonify({"error": "Invalid season format. Use YYYY-YYYY (e.g. 2025-2026)"}), 400
        
    today = datetime.now(ZoneInfo('America/New_York')).date()
    
    # Count events in this range
    events = Event.query.filter(
        Event.date >= start_date,
        Event.date <= end_date,
        Event.status != 'cancelled'
    ).all()
    
    total_nights = len(events)
    completed_nights = sum(1 for e in events if e.date < today and e.status != 'cancelled')
    future_nights = total_nights - completed_nights
    
    return jsonify({
        "season": season_str,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_nights": total_nights,
        "completed_nights": completed_nights,
        "future_nights": future_nights
    })


@api_bp.route('/season/<season_str>/detail')
def season_detail(season_str):
    start_date, end_date = get_season_dates(season_str)
    
    if not start_date:
        return jsonify({"error": "Invalid season format. Use YYYY-YYYY (e.g. 2025-2026)"}), 400
        
    # Get all events in this range
    events = Event.query.filter(
        Event.date >= start_date,
        Event.date <= end_date,
        Event.status != 'cancelled'
    ).order_by(Event.date).all()
    
    results = []
    for event in events:
        total_capacity = sum(s.capacity for s in event.shifts)
        total_confirmed = sum(s.confirmed_count for s in event.shifts)
        
        results.append({
            "date": event.date.isoformat(),
            "status": event.status,
            "volunteer_count": total_confirmed,
            "volunteer_capacity": total_capacity
        })
    
    return jsonify({
        "season": season_str,
        "nights": results
    })
