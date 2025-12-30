import datetime

import jwt
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            # Generate Token (UUID instead of JWT)
            import uuid
            token_str = str(uuid.uuid4())
            
            # Save to DB
            from app.models import LoginToken
            expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
            token_entry = LoginToken(token=token_str, user_id=user.id, expires_at=expiry)
            db.session.add(token_entry)
            db.session.commit()

            # Send Email
            # Ensure HTTPS
            link = url_for("main.validate_magic_link", token=token_str, _external=True, _scheme='https')

            from app.email import send_email

            send_email(
                "[MECWS] Login Link",
                current_app.config["MAIL_DEFAULT_SENDER"],
                [email],
                render_template("email/login_link.txt", url=link, name=user.name),
                render_template("email/login_link.html", url=link, name=user.name),
                sensitive=True
            )

        flash(
            "If your email is registered, you will receive a login link shortly.",
            "info",
        )
        return redirect(url_for("main.login"))

    return render_template("login.html")


@main_bp.route("/login/<token>")
def validate_magic_link(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    from app.models import LoginToken
    
    token_entry = LoginToken.query.filter_by(token=token).first()
    
    if not token_entry:
        flash("Invalid login link.", "danger")
        return redirect(url_for("main.login"))
        
    if token_entry.expires_at < datetime.datetime.utcnow():
        # Clean up expired token
        db.session.delete(token_entry)
        db.session.commit()
        flash("Link has expired. Please try again.", "warning")
        return redirect(url_for("main.login"))
        
    # Log in user
    user = token_entry.user
    login_user(user)
    
    # Invalidate token (one-time use)
    db.session.delete(token_entry)
    db.session.commit()
    
    flash("Successfully logged in!", "success")
    next_page = request.args.get('next')
    return redirect(next_page if next_page else url_for("main.dashboard"))


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    from app.forms import ProfileForm
    from app.extensions import db

    form = ProfileForm(obj=current_user)

    if request.method == "GET" and current_user.shift_preference:
        form.shift_preference.data = current_user.shift_preference.split(",")

    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.phone_number = form.phone_number.data
        current_user.emergency_contact = form.emergency_contact.data
        current_user.email_allowed = form.email_allowed.data

        # Format shift prefs
        if form.shift_preference.data:
            current_user.shift_preference = ",".join(form.shift_preference.data)
        else:
            current_user.shift_preference = ""

        db.session.commit()
        flash("Your profile has been updated.", "success")
        return redirect(url_for("main.profile"))

    return render_template("profile.html", form=form)
