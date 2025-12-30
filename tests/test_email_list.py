import pytest
from app.models import User, Email, db


def test_admin_email_list_supervisor(client, app):
    """Test that supervisor admin can view email logs."""

    with app.app_context():
        # Setup Data
        supervisor = User(email="super_log@test.com", role="Shelter Supervisor")
        email1 = Email(recipient="r1@test.com", subject="Sub1", status="sent")

        db.session.add_all([supervisor, email1])
        db.session.commit()

        sup_id = supervisor.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(sup_id)
        sess["_fresh"] = True

    resp = client.get("/admin/emails")
    assert resp.status_code == 200
    assert b"Sub1" in resp.data
    assert b"Sent" in resp.data


def test_admin_email_list_denied_member(client, app):
    """Test that team member is denied access."""

    with app.app_context():
        member = User(email="member_log@test.com", role="Team Member")
        db.session.add(member)
        db.session.commit()
        mem_id = member.id

    with client.session_transaction() as sess:
        sess["_user_id"] = str(mem_id)
        sess["_fresh"] = True

    resp = client.get("/admin/emails", follow_redirects=True)
    # Redirects to dashboard and shows flash
    assert b"Access denied" in resp.data
