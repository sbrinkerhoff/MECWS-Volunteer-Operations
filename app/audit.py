from datetime import datetime
from flask import current_app
from flask_login import current_user

def log_audit(action, details=None, user=None):
    """
    Log an actionable event to the application log file.
    
    :param action: Short string describing action (e.g., "login", "create_event")
    :param details: Optional longer description or JSON
    :param user: User object or ID. Defaults to current_user if available.
    """
    try:
        user_identifier = "Anonymous"
        if user:
            # If user object passed
            if hasattr(user, 'email'):
                user_identifier = f"{user.email} (ID: {user.id})"
            else:
                 user_identifier = f"User ID: {user}"
        elif current_user and current_user.is_authenticated:
            user_identifier = f"{current_user.email} (ID: {current_user.id})"
            
        log_message = f"AUDIT: [{action}] by {user_identifier} - Details: {details or 'N/A'}"
        
        # Log to the standard flask app logger (which we routed to file)
        current_app.logger.info(log_message)
        
    except Exception as e:
        print(f"FAILED TO WRITE TO AUDIT LOG: {e}")
