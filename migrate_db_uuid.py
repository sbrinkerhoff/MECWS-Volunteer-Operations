import os
import shutil
import sqlite3
import uuid
import datetime
from sqlalchemy import text
from app import create_app, db
from app.models import User, Visitor, Event, Shift, Signup, CheckIn, Email, EmailTemplate, LoginToken

# Helper to parse dates/times from SQLite strings
def parse_datetime(val):
    if not val:
        return None
    # Standard SQLite formats
    formats = [
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None

def parse_date(val):
    dt = parse_datetime(val)
    return dt.date() if dt else None

def parse_time(val):
    if not val:
        return None
    # If full datetime string is stored for Time col?
    if " " in val:
        dt = parse_datetime(val)
        return dt.time() if dt else None
        
    formats = [
        "%H:%M:%S.%f",
        "%H:%M:%S"
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(val, fmt).time()
        except ValueError:
            continue
    return None

def migrate():
    app = create_app()
    
    # Path to DB
    db_path = os.path.join(app.root_path, '../instance/mecws.db')
    db_path = os.path.abspath(db_path)
    
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return

    print(f"Starting Migration on {db_path}")
    
    # 1. Backup
    backup_path = db_path + f".bak-{uuid.uuid4().hex[:8]}"
    shutil.copy2(db_path, backup_path)
    print(f"Backup created: {backup_path}")

    # 2. Rename Tables
    tables = [
        'users', 'visitors', 'events', 'shifts', 'signups', 
        'checkins', 'emails', 'email_templates', 'login_tokens', 'alembic_version'
    ]
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Turn off FKs to allow renaming referenced tables
    cursor.execute("PRAGMA foreign_keys=OFF")
    
    existing_tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
    cursor.execute(existing_tables_query)
    existing_tables_list = [row[0] for row in cursor.fetchall()]
    
    moved_tables = []
    
    try:
        for t in tables:
            old_name = f"{t}_old"
            
            # Scenario: Both exist (e.g., failed run left _old, then Alembic created empty new t)
            if t in existing_tables_list and old_name in existing_tables_list:
                print(f"Collision: Both {t} and {old_name} exist. assuming {t} is garbage/empty from failed restart.")
                print(f"Dropping {t}...")
                cursor.execute(f"DROP TABLE {t}")
                existing_tables_list.remove(t)
                # Now fall through to the elif check below
            
            if t in existing_tables_list:
                print(f"Renaming {t} -> {old_name}")
                cursor.execute(f"ALTER TABLE {t} RENAME TO {old_name}")
                moved_tables.append(t)
            
            # Check if this table was already renamed in a previous failed run
            elif old_name in existing_tables_list:
                print(f"Found existing {old_name}, assuming previous run moved it.")
                moved_tables.append(t)
        
        conn.commit()

        # Iterate through moved tables and drop their indexes to prevent collision
        # SQLite RENAME TABLE doesn't rename indexes, so ix_users_email still points to users_old
        for t in moved_tables:
            old_table = f"{t}_old"
            print(f"Checking indexes for {old_table}...")
            cursor.execute(f"PRAGMA index_list('{old_table}')")
            indexes = cursor.fetchall()
            for idx in indexes:
                idx_name = idx['name']
                # Skip internal indexes (sqlite_autoindex_...)
                if idx_name.startswith('sqlite_autoindex'):
                    continue
                # Also skip the internal primary key index if it's unnamed but usually shown as autoindex
                print(f"Dropping index {idx_name} on {old_table} to free up name.")
                cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")
            conn.commit()

    except Exception as e:
        print(f"Error preparing tables: {e}")
        conn.close()
        return

    conn.close()

    # 3. Create New Schema
    print("Creating new schema...")
    with app.app_context():
        db.create_all()

        # 4. Migrate Data
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # ID Mappings (Old ID -> New UUID)
        user_map = {}
        visitor_map = {}
        event_map = {}
        shift_map = {}

        # --- Users ---
        if 'users' in moved_tables:
            print("Migrating Users...")
            cursor.execute("SELECT * FROM users_old")
            for row in cursor.fetchall():
                new_id = str(uuid.uuid4())
                user_map[row['id']] = new_id
                
                u = User(
                    id=new_id,
                    email=row['email'],
                    name=row['name'],
                    emergency_contact=row['emergency_contact'],
                    phone_number=row['phone_number'],
                    address_street=row['address_street'],
                    address_city=row['address_city'],
                    address_state=row['address_state'],
                    role=row['role'],
                    level=row['level'],
                    shift_preference=row['shift_preference'],
                    email_allowed=bool(row['email_allowed']) if row['email_allowed'] is not None else True,
                    notes=row['notes']
                )
                db.session.add(u)
            db.session.commit()

        # --- Visitors ---
        if 'visitors' in moved_tables:
            print("Migrating Visitors...")
            cursor.execute("SELECT * FROM visitors_old")
            for row in cursor.fetchall():
                new_id = str(uuid.uuid4())
                visitor_map[row['id']] = new_id
                v = Visitor(
                    id=new_id,
                    name=row['name'],
                    alias=row['alias']
                )
                db.session.add(v)
            db.session.commit()

        # --- Events ---
        if 'events' in moved_tables:
            print("Migrating Events...")
            cursor.execute("SELECT * FROM events_old")
            for row in cursor.fetchall():
                new_id = str(uuid.uuid4())
                event_map[row['id']] = new_id
                
                e = Event(
                    id=new_id,
                    date=parse_date(row['date']),
                    description=row['description'],
                    status=row['status']
                )
                db.session.add(e)
            db.session.commit()

        # --- Shifts ---
        if 'shifts' in moved_tables:
            print("Migrating Shifts...")
            cursor.execute("SELECT * FROM shifts_old")
            for row in cursor.fetchall():
                if row['event_id'] not in event_map:
                    print(f"Skipping shift {row['id']} (orphaned event {row['event_id']})")
                    continue
                    
                new_id = str(uuid.uuid4())
                shift_map[row['id']] = new_id
                
                s = Shift(
                    id=new_id,
                    event_id=event_map[row['event_id']],
                    start_time=parse_time(row['start_time']),
                    end_time=parse_time(row['end_time']),
                    capacity=row['capacity']
                )
                db.session.add(s)
            db.session.commit()

        # --- Signups ---
        if 'signups' in moved_tables:
            print("Migrating Signups...")
            cursor.execute("SELECT * FROM signups_old")
            for row in cursor.fetchall():
                if row['user_id'] not in user_map or row['shift_id'] not in shift_map:
                    continue
                    
                su = Signup(
                    id=str(uuid.uuid4()),
                    user_id=user_map[row['user_id']],
                    shift_id=shift_map[row['shift_id']],
                    confirmed=bool(row['confirmed']),
                    created_at=parse_datetime(row['created_at'])
                )
                db.session.add(su)
            db.session.commit()

        # --- CheckIns ---
        if 'checkins' in moved_tables:
            print("Migrating CheckIns...")
            cursor.execute("SELECT * FROM checkins_old")
            for row in cursor.fetchall():
                if row['event_id'] not in event_map or row['visitor_id'] not in visitor_map:
                    continue
                    
                ci = CheckIn(
                    id=str(uuid.uuid4()),
                    event_id=event_map[row['event_id']],
                    visitor_id=visitor_map[row['visitor_id']],
                    check_in_time=parse_datetime(row['check_in_time'])
                )
                db.session.add(ci)
            db.session.commit()

        # --- Emails ---
        if 'emails' in moved_tables:
            print("Migrating Emails...")
            cursor.execute("SELECT * FROM emails_old")
            for row in cursor.fetchall():
                em = Email(
                    id=str(uuid.uuid4()),
                    recipient=row['recipient'],
                    subject=row['subject'],
                    body_text=row['body_text'],
                    body_html=row['body_html'],
                    status=row['status'],
                    created_at=parse_datetime(row['created_at']),
                    sent_at=parse_datetime(row['sent_at']),
                    error_message=row['error_message'],
                    sensitive=bool(row['sensitive']) if 'sensitive' in row.keys() and row['sensitive'] is not None else False
                )
                db.session.add(em)
            db.session.commit()
            
        # --- Templates ---
        if 'email_templates' in moved_tables:
            print("Migrating Email Templates...")
            cursor.execute("SELECT * FROM email_templates_old")
            for row in cursor.fetchall():
                et = EmailTemplate(
                    id=str(uuid.uuid4()),
                    slug=row['slug'],
                    name=row['name'],
                    subject=row['subject'],
                    body_text=row['body_text'],
                    body_html=row['body_html']
                )
                db.session.add(et)
            db.session.commit()
            
        # --- Login Tokens ---
        if 'login_tokens' in moved_tables:
            print("Migrating Login Tokens...")
            cursor.execute("SELECT * FROM login_tokens_old")
            for row in cursor.fetchall():
                if row['user_id'] not in user_map:
                    continue
                lt = LoginToken(
                    id=str(uuid.uuid4()),
                    token=row['token'],
                    user_id=user_map[row['user_id']],
                    expires_at=parse_datetime(row['expires_at']),
                    created_at=parse_datetime(row['created_at'])
                )
                db.session.add(lt)
            db.session.commit()

        # --- Stamp Alembic Version ---
        print("Stamping Alembic Version...")
        # Create alembic_version table if not exists (db.create_all might not create it if it's not a model)
        cursor.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))")
        # clear any existing
        cursor.execute("DELETE FROM alembic_version")
        # insert head revision
        cursor.execute("INSERT INTO alembic_version (version_num) VALUES ('2b74f868250d')")
        conn.commit()

    conn.close()
    print("Migration finished successfully.")
    print("Old data is preserved in tables passing with '_old'. Drop them manually if everything looks good.")

if __name__ == "__main__":
    migrate()
