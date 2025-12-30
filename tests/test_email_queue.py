import pytest
from app.models import Email, db
from app.email import send_email


def test_email_queuing(app):
    """Test that send_email adds a record to the DB."""
    with app.app_context():
        # Clean up any existing emails (though usually clean DB per test session if configured)
        db.session.query(Email).delete()
        db.session.commit()

        initial_count = db.session.query(Email).count()
        assert initial_count == 0

        send_email(
            subject="Test Subject",
            sender="test@example.com",
            recipients=["recipient@example.com"],
            text_body="Hello",
            html_body="<b>Hello</b>",
        )

        new_count = db.session.query(Email).count()
        assert new_count == 1

        email = db.session.query(Email).first()
        assert email.subject == "Test Subject"
        assert email.recipient == "recipient@example.com"
        assert email.status == "pending"
        assert email.body_text == "Hello"
