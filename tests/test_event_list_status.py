import pytest
from datetime import date, time
from app.models import Event, Shift, Signup, User


def test_event_list_staffing_status(client, app):
    """Test that the event list page displays staffing status correctly."""

    with app.app_context():
        # Setup Data
        admin = User(
            email="admin_list_test@mecws.org", role="Shelter Supervisor", name="Admin"
        )
        event = Event(date=date(2025, 12, 31), description="Status Check Event")

        # 3 Shifts
        # Shift 1: Full (2/2)
        s1 = Shift(
            start_time=time(19, 45), end_time=time(0, 0), event=event, capacity=2
        )
        # Shift 2: Partial (1/2)
        s2 = Shift(start_time=time(0, 0), end_time=time(4, 0), event=event, capacity=2)
        # Shift 3: Empty (0/2)
        s3 = Shift(start_time=time(4, 0), end_time=time(8, 0), event=event, capacity=2)

        # Create Users for Signups
        u1 = User(email="u1@test.com")
        u2 = User(email="u2@test.com")
        u3 = User(email="u3@test.com")

        from app.models import db

        db.session.add_all([admin, event, s1, s2, s3, u1, u2, u3])
        db.session.commit()

        # Signups
        # Shift 1 Full
        db.session.add(Signup(user_id=u1.id, shift_id=s1.id, confirmed=True))
        db.session.add(Signup(user_id=u2.id, shift_id=s1.id, confirmed=True))

        # Shift 2 Partial
        db.session.add(Signup(user_id=u3.id, shift_id=s2.id, confirmed=True))

        db.session.commit()

        admin_id = admin.id

    # Login
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_id)
        sess["_fresh"] = True

    # Get Page
    resp = client.get("/admin/events")
    assert resp.status_code == 200

    html = resp.data.decode("utf-8")

    # Check for Shift 1 Status (success color, 2/2)
    # Using regex to match flexible localized time if needed, but simple string search first
    # 19:45 is 07:45 PM
    assert "text-success" in html
    assert "07:45: 2/2" in html

    # Check for Shift 2 Status (warning color, 1/2)
    # 00:00 is 12:00 AM
    assert "text-warning" in html
    assert "12:00: 1/2" in html

    # Check for Shift 3 Status (secondary color, 0/2)
    # 04:00 is 04:00 AM
    assert "text-secondary" in html
    assert "04:00: 0/2" in html
