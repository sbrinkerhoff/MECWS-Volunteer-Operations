
from datetime import date, time
from app import create_app, db
from app.models import Event, Shift

def run():
    app = create_app()
    with app.app_context():
        # Dates to check/fix
        target_dates = [
            date(2026, 1, 27),
            date(2026, 1, 28),
            date(2026, 1, 29),
            date(2026, 1, 30),
        ]
        
        # Standard Shifts
        shift_times = [
            (time(19, 45), time(0, 0)),  # Shift 1
            (time(0, 0), time(4, 0)),    # Shift 2
            (time(4, 0), time(8, 0)),    # Shift 3
        ]
        
        print(f"Checking shifts for {target_dates}...")
        
        for d in target_dates:
            # Get or Create Event
            event = Event.query.filter_by(date=d).first()
            if not event:
                event = Event(date=d, status="confirmed") # Assume confirmed if in the sheet
                db.session.add(event)
                db.session.commit()
                print(f"Created missing event for {d}")
            else:
                print(f"Event exists for {d}")
                
            # Ensure 3 shifts exist
            current_shifts = Shift.query.filter_by(event_id=event.id).count()
            if current_shifts < 3:
                print(f"  Only found {current_shifts} shifts. Adding missing ones...")
                for start, end in shift_times:
                    exists = Shift.query.filter_by(event_id=event.id, start_time=start).first()
                    if not exists:
                        new_shift = Shift(event_id=event.id, start_time=start, end_time=end)
                        db.session.add(new_shift)
                        print(f"    Added shift {start}-{end}")
                db.session.commit()
            else:
                print(f"  All 3 shifts exist.")
                
        print("Done.")

if __name__ == "__main__":
    run()
