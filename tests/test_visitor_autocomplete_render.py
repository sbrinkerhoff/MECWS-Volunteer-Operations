import pytest
from app.models import User, Event, Visitor


def test_view_event_visitor_list_presence(client, app):
    """Test that the view_event page contains the visitor list for autocomplete."""
    with app.app_context():
        # Ensure data exists (User, Event, Visitor)
        # We rely on the DB being seeded or clean state from fixture
        # Creating fresh ensures we know what we are looking for
        admin = User(
            email="admin_page_test@mecws.org", role="Shelter Supervisor", name="Admin"
        )
        from datetime import date

        event = Event(date=date(2025, 12, 31), description="Test Event")
        visitor = Visitor(name="AutocompleteUser", alias="AU")

        from app.models import db

        db.session.add_all([admin, event, visitor])
        db.session.commit()

        admin_id = admin.id
        event_id = event.id

    # Login
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_id)
        sess["_fresh"] = True

    # Get Page
    resp = client.get(f"/admin/events/{event_id}")
    assert resp.status_code == 200

    html = resp.data.decode("utf-8")

    # Check for the JS array population
    # It should look like: "AutocompleteUser"
    assert '"AutocompleteUser"' in html

    # Check that search-visitor-input class exists
    assert 'class="form-control form-control-sm search-visitor-input"' in html
