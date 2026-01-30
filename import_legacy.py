
import pandas as pd
import re
from datetime import datetime, time, date
from app import create_app, db
from app.models import Event, Shift, User, Signup

def clean_name(text):
    if pd.isna(text): return None
    text = str(text).strip()
    if not text: return None
    
    # Remove phone numbers
    # Strategy: Split at the first occurrence of a digit
    match = re.search(r'\d', text)
    if match:
        text = text[:match.start()]
    
    # Clean up trailing content
    text = text.strip()
    # Remove trailing dashes or parens if any
    text = text.strip(" -()")
    
    if not text: return None
    return text

def parse_date_str(date_text):
    if pd.isna(date_text): return None
    date_text = str(date_text)
    
    # Expected format: "Sun-Mon 12/7-8" or similar
    # Regex to find Month/Day
    match = re.search(r'(\d{1,2})/(\d{1,2})', date_text)
    if not match:
        return None
        
    month = int(match.group(1))
    day = int(match.group(2))
    
    # Deduce Year
    # Assumption: Data is from late 2025 to early 2026 based on "Sun-Mon 12/7" matching 2025
    year = 2025
    if month < 7: # If Jan-Jun, assume 2026
        year = 2026
        
    return date(year, month, day)

def get_or_create_user(name):
    # Try exact match
    user = User.query.filter(User.name.ilike(name)).first()
    if user:
        return user
        
    # Try fuzzy/partial match if name is "First Last" vs "First M. Last"?
    # For now, let's create if not found to ensure data is imported.
    # We need a unique email.
    slug = name.lower().replace(" ", ".")
    email = f"{slug}@placeholder.mecws.org"
    
    # Check if email taken
    if User.query.filter_by(email=email).first():
        # Append random digits if collision
        import random
        email = f"{slug}.{random.randint(100,999)}@placeholder.mecws.org"
        
    user = User(name=name, email=email, role="Team Member")
    db.session.add(user)
    db.session.commit() # Commit immediately to get ID
    print(f"Created new user: {name} ({email})")
    return user

def run_import():
    app = create_app()
    with app.app_context():
        print("Reading Excel file...")
        df = pd.read_excel('volunteer_events.xlsx')
        
        # Forward fill the Dates
        df['OPEN DATES'] = df['OPEN DATES'].ffill()
        
        # Filter out rows that are purely empty spacers (where Shifts are null)
        # Actually, keep rows that have ANY shift data
        shift_cols = ['Shift 1 - 7:45PM-12', 'Shift 2 - 12-4AM', 'Shift 3 - 4AM-8:30']
        
        # Iterate
        current_event = None
        current_date_obj = None
        
        # Shift definitions (approximate times)
        shift_times = [
            (time(19, 45), time(0, 0)),  # Shift 1
            (time(0, 0), time(4, 0)),    # Shift 2
            (time(4, 0), time(8, 0)),    # Shift 3
        ]
        
        for index, row in df.iterrows():
            date_str = row['OPEN DATES']
            parsed = parse_date_str(date_str)
            
            if not parsed:
                continue
                
            # Create/Get Event
            if current_date_obj != parsed:
                current_date_obj = parsed
                current_event = Event.query.filter_by(date=current_date_obj).first()
                if not current_event:
                    current_event = Event(date=current_date_obj, status="confirmed")
                    db.session.add(current_event)
                    db.session.commit()
                    print(f"Created Event: {current_date_obj}")
                
                # Append Coordinators to description if present in the first row of the block
                open_coord = clean_name(row.get('OPENING COORDINATOR'))
                close_coord = clean_name(row.get('CLOSING COORDINATOR'))
                desc_parts = []
                if open_coord: desc_parts.append(f"Opening Coordinator: {open_coord}")
                if close_coord: desc_parts.append(f"Closing Coordinator: {close_coord}")
                
                if desc_parts:
                    new_desc = "; ".join(desc_parts)
                    if current_event.description:
                        current_event.description += "; " + new_desc
                    else:
                        current_event.description = new_desc
                    db.session.commit()

            # Process Shifts
            # There are 3 shift columns.
            for i, col_name in enumerate(shift_cols):
                raw_name = row.get(col_name)
                volunteer_name = clean_name(raw_name)
                
                if volunteer_name:
                    start_t, end_t = shift_times[i]
                    
                    # Find specific shift for this event
                    shift = Shift.query.filter_by(event_id=current_event.id, start_time=start_t).first()
                    
                    if not shift:
                        shift = Shift(event_id=current_event.id, start_time=start_t, end_time=end_t)
                        db.session.add(shift)
                        db.session.commit()
                        
                    # Find User
                    user = get_or_create_user(volunteer_name)
                    
                    # Create Signup if not exists
                    signup = Signup.query.filter_by(shift_id=shift.id, user_id=user.id).first()
                    if not signup:
                        signup = Signup(shift_id=shift.id, user_id=user.id, confirmed=True)
                        db.session.add(signup)
                        print(f"  Assigned {volunteer_name} to Shift {i+1} on {current_date_obj}")
                    else:
                        print(f"  {volunteer_name} already assigned to Shift {i+1} on {current_date_obj}")
                        
        db.session.commit()
        print("Import Complete.")

if __name__ == "__main__":
    run_import()
