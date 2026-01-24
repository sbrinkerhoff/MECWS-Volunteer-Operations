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
        supervisor = User(email="stan@vtwireless.com", role="Shelter Supervisor")
        volunteer = User(email="volunteer@mecws.org", role="Team Member")

        db.session.add(supervisor)
        db.session.add(volunteer)
        db.session.commit()

        print("Created admin@mecws.org (Supervisor)")
        print("Created volunteer@mecws.org (Team Member)")


if __name__ == "__main__":
    seed()
