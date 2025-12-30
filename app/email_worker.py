import time
import threading
from datetime import datetime
from flask_mail import Message
from app.extensions import db, mail
from app.models import Email


def start_email_worker(app):
    """
    Starts a background thread that checks for pending emails every 15 seconds
    and sends them using the configured mail server.
    """

    def worker():
        # Ensure we work within the application context
        with app.app_context():
            print("Email worker started.")
            while True:
                try:
                    # Find pending emails
                    # Limit to avoid memory issues if backed up, but strictly request said "emails to send"
                    pending_emails = (
                        Email.query.filter_by(status="pending")
                        .order_by(Email.created_at)
                        .limit(50)
                        .all()
                    )

                    if pending_emails:
                        print(
                            f"Email Worker: Found {len(pending_emails)} pending emails."
                        )

                    for email_record in pending_emails:
                        try:
                            # Construct Message
                            msg = Message(
                                subject=email_record.subject,
                                recipients=[email_record.recipient],
                                body=email_record.body_text,
                                html=email_record.body_html,
                                sender=app.config.get("MAIL_DEFAULT_SENDER"),
                            )

                            # Send
                            mail.send(msg)

                            # Update Status
                            email_record.status = "sent"
                            email_record.sent_at = datetime.utcnow()
                            print(
                                f"Email Worker: Sent email {email_record.id} to {email_record.recipient}"
                            )

                        except Exception as e:
                            # Handle Failure
                            email_record.status = "failed"
                            email_record.error_message = str(e)
                            print(
                                f"Email Worker: Failed to send email {email_record.id}: {e}"
                            )

                        # Commit update
                        db.session.commit()

                except Exception as e:
                    print(f"Email Worker Error: {e}")
                    # Prevent tight loop on extensive DB error
                    time.sleep(5)

                time.sleep(15)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread
