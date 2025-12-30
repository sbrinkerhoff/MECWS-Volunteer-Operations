from app.extensions import db
from app.models import Email


def send_email(subject, sender, recipients, text_body, html_body, sensitive=False):
    """
    Queue an email to be sent by an external provider/script.
    Writes the email details to the 'emails' database table.
    """
    try:
        for recipient in recipients:
            email = Email(
                recipient=recipient,
                subject=subject,
                body_text=text_body,
                body_html=html_body,
                status="pending",
                sensitive=sensitive
            )
            db.session.add(email)

        db.session.commit()
    except Exception as e:
        print(f"Failed to queue email: {e}")
        db.session.rollback()
