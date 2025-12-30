from datetime import date, time

import pytest

from app.models import Event, Shift, Signup, User, db


@pytest.fixture
def data_setup(app):
    with app.app_context():
        # Users
        admin = User(
            email="admin@mecws.org", name="Admin User", role="Shelter Supervisor"
        )
        u1 = User(email="john@example.com", name="John Doe", role="Team Member")
        u2 = User(email="jane@example.com", name="Jane Smith", role="Team Member")

        # Event & Shift
        event = Event(date=date(2025, 12, 31), description="NYE Shelter")
        db.session.add_all([admin, u1, u2, event])
        db.session.commit()

        shift = Shift(
            start_time=time(20, 0), end_time=time(0, 0), event_id=event.id, capacity=2
        )
        db.session.add(shift)
        db.session.commit()

        return {
            "admin_id": admin.id,
            "u1_id": u1.id,
            "u2_id": u2.id,
            "shift_id": shift.id,
            "event_id": event.id,
        }


def login_as(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def test_assign_volunteer_lookup_formats(client, app, data_setup):
    """Test the admin route logic for various user identifier inputs."""

    login_as(client, data_setup["admin_id"])
    shift_id = data_setup["shift_id"]

    # 1. Test "Name <email>" format (Standard Autocomplete)
    resp = client.post(
        f"/admin/shifts/{shift_id}/assign",
        data={"user_identifier": "John Doe <john@example.com>"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"assigned successfully" in resp.data

    # Verify DB
    with app.app_context():
        signup = Signup.query.filter_by(
            user_id=data_setup["u1_id"], shift_id=shift_id
        ).first()
        assert signup is not None
        assert signup.confirmed is True

        # Clean up for next test
        db.session.delete(signup)
        db.session.commit()

    # 2. Test "Email Only"
    resp = client.post(
        f"/admin/shifts/{shift_id}/assign",
        data={"user_identifier": "john@example.com"},
        follow_redirects=True,
    )
    assert b"assigned successfully" in resp.data

    with app.app_context():
        signup = Signup.query.filter_by(
            user_id=data_setup["u1_id"], shift_id=shift_id
        ).first()
        db.session.delete(signup)
        db.session.commit()

    # 3. Test "Name Only"
    resp = client.post(
        f"/admin/shifts/{shift_id}/assign",
        data={"user_identifier": "John Doe"},
        follow_redirects=True,
    )
    assert b"assigned successfully" in resp.data

    with app.app_context():
        signup = Signup.query.filter_by(
            user_id=data_setup["u1_id"], shift_id=shift_id
        ).first()
        db.session.delete(signup)
        db.session.commit()

    # 4. Test "Fuzzy Name" (First Name)
    resp = client.post(
        f"/admin/shifts/{shift_id}/assign",
        data={"user_identifier": "John"},
        follow_redirects=True,
    )
    assert b"assigned successfully" in resp.data

    with app.app_context():
        signup = Signup.query.filter_by(
            user_id=data_setup["u1_id"], shift_id=shift_id
        ).first()
        db.session.delete(signup)
        db.session.commit()


def test_assign_volunteer_failures(client, app, data_setup):
    """Test failure cases for assignment."""
    login_as(client, data_setup["admin_id"])
    shift_id = data_setup["shift_id"]

    # Non-existent user
    resp = client.post(
        f"/admin/shifts/{shift_id}/assign",
        data={"user_identifier": "Ghost User"},
        follow_redirects=True,
    )
    assert b"Could not find a user" in resp.data


def test_duplicate_assignment_prevention(client, app, data_setup):
    """Ensure a user cannot be assigned twice to the same shift."""
    login_as(client, data_setup["admin_id"])
    shift_id = data_setup["shift_id"]

    # First sign up
    client.post(
        f"/admin/shifts/{shift_id}/assign", data={"user_identifier": "john@example.com"}
    )

    # Try again
    resp = client.post(
        f"/admin/shifts/{shift_id}/assign",
        data={"user_identifier": "john@example.com"},
        follow_redirects=True,
    )

    assert b"User is already assigned" in resp.data

    with app.app_context():
        count = Signup.query.filter_by(
            user_id=data_setup["u1_id"], shift_id=shift_id
        ).count()
        assert count == 1
