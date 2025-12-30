from datetime import date, time

from app.models import Event, Shift, Signup, User, db


def test_user_creation(app):
    user = User(email="test@example.com", role="Team Member")
    db.session.add(user)
    db.session.commit()
    assert User.query.count() == 1
    assert user.role == "Team Member"


def test_event_shift_creation(app):
    event = Event(date=date(2025, 12, 25), description="Xmas Shelter")
    db.session.add(event)
    db.session.commit()

    shift = Shift(event_id=event.id, start_time=time(20, 0), end_time=time(0, 0))
    db.session.add(shift)
    db.session.commit()

    assert Event.query.count() == 1
    assert Shift.query.count() == 1
    assert shift.event == event


def test_signup_flow(app):
    # Setup
    u = User(email="vol@example.com")
    e = Event(date=date(2025, 1, 1))
    db.session.add_all([u, e])
    db.session.commit()

    s = Shift(event_id=e.id, start_time=time(18, 0), end_time=time(20, 0))
    db.session.add(s)
    db.session.commit()

    # Signup
    signup = Signup(user_id=u.id, shift_id=s.id)
    db.session.add(signup)
    db.session.commit()

    assert Signup.query.count() == 1
    assert not signup.confirmed

    # Confirm
    signup.confirmed = True
    db.session.commit()
    assert signup.confirmed
