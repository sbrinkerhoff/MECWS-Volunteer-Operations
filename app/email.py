from app.extensions import db
from app.models import Email


def send_email(subject, sender, recipients, text_body, html_body, sensitive=False):
    """
    Queue an email to be sent by an external provider/script.
    Writes the email details to the 'emails' database table.
    """
    from flask import url_for, render_template_string
    from app.models import User, EmailTemplate

    # Standard Footer Content
    footer_text = (
        "\n\n---\n"
        "This email was sent by Montpelier Emergency Cold Weather Shelter Inc.\n"
        "Our mailing address is PO Box 394, Montpelier, VT, 05601.\n"
        "To unsubscribe from future emails, please visit: {unsubscribe_url}"
    )
    footer_html = (
        "<br><br><hr>"
        "<p style='font-size: 12px; color: #666;'>"
        "This email was sent by <i>Montpelier Emergency Cold Weather Shelter Inc</i>.<br>"
        "Our mailing address is PO Box 394, Montpelier, VT, 05601.<br>"
        "<a href='{unsubscribe_url}'>Unsubscribe</a>"
        "</p>"
    )

    try:
        count = 0
        for recipient in recipients:
            user = User.query.filter_by(email=recipient).first()
            
            # Check unsubscribe status for non-sensitive emails
            if not sensitive:
                if user and user.unsubscribe_requested:
                    print(f"Skipping email to {recipient} (Unsubscribe Requested)")
                    continue
            
            # Note: Footer is now handled by the templates themselves.
            email = Email(
                recipient=recipient,
                subject=subject,
                body_text=text_body,
                body_html=html_body,
                status="pending",
                sensitive=sensitive
            )
            db.session.add(email)
            count += 1

        db.session.commit()
        
        # Log successful queue
        from app.audit import log_audit
        log_audit("send_email", f"Queued {count} emails (requested {len(recipients)}). Subject: {subject}")

    except Exception as e:
        # Log failure
        from app.audit import log_audit
        log_audit("send_email_error", f"Failed to queue. Subject: {subject}. Error: {e}")
        
        print(f"Failed to queue email: {e}")
        db.session.rollback()
