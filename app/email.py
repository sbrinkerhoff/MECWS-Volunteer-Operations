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
        
        # Log successful queue
        from app.audit import log_audit
        log_audit("send_email", f"Queued {len(recipients)} emails. Subject: {subject}")

    except Exception as e:
        # Log failure
        from app.audit import log_audit
        log_audit("send_email_error", f"Failed to queue. Subject: {subject}. Error: {e}")
        
        print(f"Failed to queue email: {e}")
        db.session.rollback()
