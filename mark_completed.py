
from datetime import date
from app import create_app, db
from app.models import Event

def run():
    app = create_app()
    with app.app_context():
        # Use server today
        today = date.today()
        print(f"Running cleanup for events before {today}")
        
        # Find matches: date < today, AND status NOT in [completed, cancelled]
        events_to_update = Event.query.filter(
            Event.date < today,
            Event.status != 'cancelled',
            Event.status != 'completed'
        ).all()
        
        if not events_to_update:
            print("No past events found that need updating.")
            return

        print(f"Found {len(events_to_update)} past events to complete.")
        
        for event in events_to_update:
            print(f" - Marking {event.date} (was {event.status}) -> completed")
            event.status = "completed"
            
        db.session.commit()
        print("Done.")

if __name__ == "__main__":
    run()
