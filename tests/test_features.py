from datetime import date, time

from app.models import CheckIn, Event, Shift, Signup, User, Visitor, db


def test_user_attributes(app):
    """Test the new user attributes (level, shift_preference) and Name."""
    with app.app_context():
        u = User(
            email="test@example.com",
            name="Test Volunteer",
            level="Advanced",
            shift_preference="7:45PM-12AM,4AM-8AM",
        )
        db.session.add(u)
        db.session.commit()

        fetched = User.query.filter_by(email="test@example.com").first()
        assert fetched.name == "Test Volunteer"
        assert fetched.level == "Advanced"
        assert "7:45PM-12AM" in fetched.shift_preference


def test_visitor_checkin_flow(app):
    """Test creating a visitor, an event, and checking them in."""
    with app.app_context():
        # Setup
        v = Visitor(name="John Doe", alias="JD")
        e = Event(date=date.today(), description="Cold Night")
        db.session.add_all([v, e])
        db.session.commit()

        # Check In
        checkin = CheckIn(visitor_id=v.id, event_id=e.id)
        db.session.add(checkin)
        db.session.commit()

        # Verify relationships
        assert v.checkins.count() == 1
        assert e.checkins.count() == 1
        assert e.checkins.first().visitor.name == "John Doe"


def test_admin_assign_volunteer(app):
    """Test manual assignment of a volunteer to a shift."""
    with app.app_context():
        # Setup
        u = User(email="volunteer@mecws.org", name="Volunteer Vic")
        e = Event(date=date.today(), description="Test Event")
        db.session.add_all([u, e])
        db.session.commit()

        # Create shift manually as auto-generation is in the route, not model
        s = Shift(start_time=time(20, 0), end_time=time(0, 0), event_id=e.id)
        db.session.add(s)
        db.session.commit()

        # Assign
        signup = Signup(user_id=u.id, shift_id=s.id, confirmed=True)
        db.session.add(signup)
        db.session.commit()

        # Verify
        assert s.signups.count() == 1
        assert s.signups.first().confirmed is True
        assert s.signups.first().volunteer.name == "Volunteer Vic"


def test_search_logic(app):
    """Test the filtering logic used in the search route."""
    with app.app_context():
        u1 = User(email="alice@example.com", name="Alice")
        u2 = User(email="bob@example.com", name="Bob")
        u3 = User(email="carol@example.com", name="Carol")
        db.session.add_all([u1, u2, u3])
        db.session.commit()

        # Search by name 'Al'
        results_name = User.query.filter(
            (User.email.ilike("%Al%")) | (User.name.ilike("%Al%"))
        ).all()
        assert len(results_name) == 1
        assert results_name[0].name == "Alice"

        # Search by email 'example'
        results_email = User.query.filter(
            (User.email.ilike("%example%")) | (User.name.ilike("%example%"))
        ).all()
        assert len(results_email) == 3


def test_dashboard_access(client, app):
    """Test that the dashboard renders without template errors."""
    with app.app_context():
        u = User(email="test@example.com", name="Tester", role="Shelter Supervisor")
        db.session.add(u)
        db.session.commit()
        user_id = u.id

    # Simulate login
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data
