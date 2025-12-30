from datetime import datetime

from flask_login import UserMixin

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    emergency_contact = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    role = db.Column(
        db.String(50), default="Team Member"
    )  # 'Shelter Supervisor' or 'Team Member'
    level = db.Column(
        db.String(50), default="Beginner"
    )  # 'Beginner', 'Intermediate', 'Advanced'
    shift_preference = db.Column(db.String(50))  # '7:45PM-12AM', '12AM-4AM', '4AM-8AM'
    email_allowed = db.Column(db.Boolean, default=True)

    signups = db.relationship("Signup", backref="volunteer", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email}>"


class Visitor(db.Model):
    __tablename__ = "visitors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    alias = db.Column(db.String(100))

    def __repr__(self):
        return f"<Visitor {self.alias or self.name}>"


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="planned")  # 'active' or 'planned'

    shifts = db.relationship(
        "Shift", backref="event", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Event {self.date}>"


class Shift(db.Model):
    __tablename__ = "shifts"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    # "Each shift requires two people to staff it."
    capacity = db.Column(db.Integer, default=2)

    signups = db.relationship(
        "Signup", backref="shift", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Shift {self.start_time}-{self.end_time}>"

    @property
    def confirmed_count(self):
        return self.signups.filter_by(confirmed=True).count()


class Signup(db.Model):
    __tablename__ = "signups"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    shift_id = db.Column(db.Integer, db.ForeignKey("shifts.id"), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Signup User:{self.user_id} Shift:{self.shift_id}>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class CheckIn(db.Model):
    __tablename__ = "checkins"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    visitor_id = db.Column(db.Integer, db.ForeignKey("visitors.id"), nullable=False)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship("Event", backref=db.backref("checkins", lazy="dynamic"))
    visitor = db.relationship("Visitor", backref=db.backref("checkins", lazy="dynamic"))

    def __repr__(self):
        return f"<CheckIn Event:{self.event_id} Visitor:{self.visitor_id}>"


class Email(db.Model):
    __tablename__ = "emails"

    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body_text = db.Column(db.Text)
    body_html = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending, sent, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    sensitive = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Email {self.id} to {self.recipient}>"


class EmailTemplate(db.Model):
    __tablename__ = "email_templates"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(
        db.String(50), unique=True, nullable=False, index=True
    )  # e.g. 'signup_confirmation'
    name = db.Column(db.String(100), nullable=False)  # Human readable name
    subject = db.Column(db.String(255), nullable=False)
    body_text = db.Column(db.Text)
    body_html = db.Column(db.Text)

    def __repr__(self):
        return f"<EmailTemplate {self.slug}>"


class LoginToken(db.Model):
    __tablename__ = "login_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("login_tokens", lazy="dynamic"))

    def __repr__(self):
        return f"<LoginToken {self.token}>"
