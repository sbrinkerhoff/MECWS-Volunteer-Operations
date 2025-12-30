from app import create_app, db
from app.models import Event, Shift, Signup, User, Visitor

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "User": User,
        "Visitor": Visitor,
        "Event": Event,
        "Shift": Shift,
        "Signup": Signup,
    }


# Start Email Worker
# We move this to module level so 'flask run' picks it up.
# We add a check to avoid starting it twice when reloader is active (in debug mode)
import os

if (
    os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    or os.environ.get("FLASK_RUN_FROM_CLI") != "true"
):
    # Try/Except to avoid import errors if dependencies missing during init
    try:
        from app.email_worker import start_email_worker

        start_email_worker(app)
    except Exception as e:
        print(f"Could not start email worker: {e}")

if __name__ == "__main__":
    app.run(debug=True)
