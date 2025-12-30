import pytest
from app.models import User, db


def test_profile_update(client, app):
    """Test user can update their profile."""

    with app.app_context():
        user = User(
            email="profile_tester@test.com", name="Original Name", role="Team Member"
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    # Login
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    # GET profile
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert b"Original Name" in resp.data

    # POST update
    resp = client.post(
        "/profile",
        data={
            "name": "Updated Name",
            "phone_number": "555-0199",
            "csrf_token": "",  # handling csrf disabled in test config usually?
        },
        follow_redirects=True,
    )

    assert resp.status_code == 200
    assert b"Your profile has been updated" in resp.data
    assert b"Updated Name" in resp.data

    with app.app_context():
        u = db.session.get(User, user_id)
        assert u.name == "Updated Name"
        assert u.phone_number == "555-0199"
