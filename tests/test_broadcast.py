import pytest
from datetime import date
from app.models import Event, User, Email, LoginToken, db

def test_broadcast_email_functionality(client, app):
    """Test the broadcast email feature including subject prefix and magic link generation."""
    with app.app_context():
        # Setup Data
        supervisor = User(email="super@test.com", role="Shelter Supervisor", name="Supervisor")
        # Creating two volunteers: one allowing emails, one not (if we were testing filtering, but here simple case first)
        vol1 = User(email="vol1@test.com", role="Team Member", name="Vol One", email_allowed=True)
        vol2 = User(email="vol2@test.com", role="Team Member", name="Vol Two", email_allowed=False)
        
        event = Event(date=date(2025, 12, 30), description="Broadcast Event")
        
        db.session.add_all([supervisor, vol1, vol2, event])
        db.session.commit()
        
        supervisor_id = supervisor.id
        event_id = event.id
        vol1_id = vol1.id

    # Simulate Supervisor Login
    with client.session_transaction() as sess:
        sess["_user_id"] = str(supervisor_id)
        sess["_fresh"] = True

    # 1. Test GET request (pre-fill)
    resp = client.get(f"/admin/events/{event_id}/broadcast")
    assert resp.status_code == 200
    assert b"Volunteers Needed" in resp.data

    # 2. Test POST request (sending)
    data = {
        "subject": "Urgent Help Needed",
        "message": "Hi {{ name }}, please help on {{ date }}. Link: {{ link }}"
    }
    
    # Follow redirects to check flash message
    resp = client.post(f"/admin/events/{event_id}/broadcast", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Broadcast sent to 1 volunteers" in resp.data # only vol1 allows emails

    # 3. Verify Email Content
    with app.app_context():
        # Check that email was queued
        email = Email.query.filter_by(recipient="vol1@test.com").first()
        assert email is not None
        
        # Check Subject Prefix
        assert email.subject == "[MECWS] Urgent Help Needed"
        
        # Check Variable Replacement in Body
        assert "Hi Vol One" in email.body_text
        assert "December 30, 2025" in email.body_text
        
        # Check link generation
        assert "http" in email.body_text
        # We can't easily check the token validity without parsing, but we can check a token exists for the user
        token = LoginToken.query.filter_by(user_id=vol1_id).first()
        assert token is not None
        assert token.token in email.body_text
