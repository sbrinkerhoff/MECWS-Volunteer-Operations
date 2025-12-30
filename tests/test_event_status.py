import pytest
from datetime import date
from app.models import Event, User


def test_event_visibility_by_status(client, app):
    """Test that 'planned' events are hidden from non-supervisors."""

    with app.app_context():
        # Clean up
        from app.models import db, Shift
        from datetime import time

        db.drop_all()
        db.create_all()

        # Setup Data
        supervisor = User(email="super@test.com", role="Shelter Supervisor")
        member = User(email="member@test.com", role="Team Member")

        # 1. Active Event (visible to all)
        e_active = Event(date=date.today(), description="Active Event", status="active")
        
        # 2. Planned Event (visible only to supervisor)
        e_planned = Event(
            date=date.today(), description="Planned Event", status="planned"
        )
        
        db.session.add_all([supervisor, member, e_active, e_planned])
        db.session.commit()
        
        # Add shifts so they appear in the list view
        s1 = Shift(event_id=e_active.id, start_time=time(8,0), end_time=time(12,0))
        s2 = Shift(event_id=e_planned.id, start_time=time(8,0), end_time=time(12,0))
        db.session.add_all([s1, s2])
        db.session.commit()

        mem_id = member.id

    # Test Member View
    with client.session_transaction() as sess:
        sess["_user_id"] = str(mem_id)
        sess["_fresh"] = True

    resp = client.get("/volunteer/shifts")
    assert resp.status_code == 200
    assert b"Active Event" in resp.data
    # formerly this was hidden, now it should be visible
    assert b"Planned Event" in resp.data


def test_event_visibility_supervisor(client, app):
    """Test that 'planned' events are visible to supervisors."""

    with app.app_context():
        # Setup Data (Clean DB assumed or handled by fixture, but let's ensure specific data)
        from app.models import db, User, Event, Shift
        from datetime import time
        
        supervisor = User(email="super_vis@test.com", role="Shelter Supervisor")
        # Ensure we have events
        e_active = Event(
            date=date(2025, 12, 30), description="Active Event Vis", status="active"
        )
        e_planned = Event(
            date=date(2025, 12, 31), description="Planned Event Vis", status="planned"
        )

        db.session.add_all([supervisor, e_active, e_planned])
        db.session.commit()
        
        # Add shifts
        s1 = Shift(event_id=e_active.id, start_time=time(8,0), end_time=time(12,0))
        s2 = Shift(event_id=e_planned.id, start_time=time(8,0), end_time=time(12,0))
        db.session.add_all([s1, s2])
        db.session.commit()

        sup_id = supervisor.id

    # Test Supervisor View
    with client.session_transaction() as sess:
        sess["_user_id"] = str(sup_id)
        sess["_fresh"] = True

    resp = client.get("/volunteer/shifts")
    assert resp.status_code == 200
    assert b"Active Event Vis" in resp.data
    assert b"Planned Event Vis" in resp.data
