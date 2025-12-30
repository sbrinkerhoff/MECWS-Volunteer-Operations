import pytest
from app.models import User, db


def test_create_event_page_renders_with_weather(client, app):
    """Test that create event page renders successfully and includes weather section."""

    with app.app_context():
        # Clean/Setup
        db.create_all()
        admin = User(email="weather_admin@test.com", role="Shelter Supervisor")
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_id)
        sess["_fresh"] = True

    resp = client.get("/admin/events/new")
    assert resp.status_code == 200

    # Check for Weather Guidance text
    assert b"Weather Guidance" in resp.data
    # Check for calendar grid existence (css class)
    assert b"calendar-grid" in resp.data
