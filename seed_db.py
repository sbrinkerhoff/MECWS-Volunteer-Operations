from app import create_app, db
from app.models import User

app = create_app()


def seed():
    with app.app_context():
        # Check if users exist
        if User.query.first():
            print("Database already seeded.")
            return

        supervisor = User(email="admin@mecws.org", role="Shelter Supervisor")
        # Wait, I didn't add 'name' to User model in Step 72, checking...
        # Requirements said Team has Email, Emergency Contact, Phone Number, Roles.
        # Visitor has Name.
        # Team is User. Does User have name?
        # Checked `app/models.py`: User has `email`, `emergency_contact`, `phone_number`, `role`. NO NAME.
        # Visitor has `name`.
        # I should probably add a defined Name to User if it's meant to be human readable?
        # Re-reading requirements: "Team... Email Address, Emergency Contact, Phone Number, Roles". No Name explicitly listed.
        # But "Visitor... Name".
        # It's weird for Team to not have a name. I'll add `name` or `full_name` to User model as an improvement, or stick to requirements.
        # I'll stick to strict requirements for now. If user is strictly defined by email, okay.

        supervisor = User(email="admin@mecws.org", role="Shelter Supervisor")
        volunteer = User(email="volunteer@mecws.org", role="Team Member")

        db.session.add(supervisor)
        db.session.add(volunteer)
        db.session.commit()

        print("Created admin@mecws.org (Supervisor)")
        print("Created volunteer@mecws.org (Team Member)")


if __name__ == "__main__":
    seed()
