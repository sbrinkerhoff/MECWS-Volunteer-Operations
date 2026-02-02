
from datetime import date
from flask import Blueprint, jsonify
from app.models import Event

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/event/today')
def event_today():
    today = date.today()
    event = Event.query.filter_by(date=today).first()
    
    if event:
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
