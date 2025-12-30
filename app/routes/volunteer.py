from datetime import date

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import Event, Shift, Signup, db

volunteer_bp = Blueprint("volunteer", __name__, url_prefix="/volunteer")


@volunteer_bp.route("/shifts")
@login_required
def available_shifts():
    # Only show future or today's events
    # Only show future or today's events
    query = Event.query.filter(Event.date >= date.today())

    # query = Event.query.filter(Event.date >= date.today())
    query = Event.query.filter(Event.date >= date.today())

    events = query.order_by(Event.date).all()
    print(
        f"DEBUG: User={current_user.email}, Role={current_user.role}, Events={len(events)}"
    )
    return render_template("volunteer/available_shifts.html", events=events)


@volunteer_bp.route("/signup/<int:shift_id>", methods=["POST"])
@login_required
def signup(shift_id):
    shift = Shift.query.get_or_404(shift_id)

    # Check if already signed up
    if shift.signups.filter_by(user_id=current_user.id).first():
        flash("You are already signed up for this shift.", "warning")
        return redirect(url_for("volunteer.available_shifts"))

    # Check capacity
    if shift.signups.count() >= shift.capacity:
        flash("This shift is full.", "danger")
        return redirect(url_for("volunteer.available_shifts"))

    # Create signup (unconfirmed by default)
    signup_entry = Signup(user_id=current_user.id, shift_id=shift.id, confirmed=False)
    db.session.add(signup_entry)
    db.session.commit()

    # Mock Notification
    # print(f"NOTIFICATION: User {current_user.email} signed up for Shift {shift.id}. Supervisor needs to confirm.")

    # Notify Supervisors
    from flask import current_app

    from app.email import send_email
    from app.models import User

    supervisors = User.query.filter_by(role="Shelter Supervisor").all()
    # Filter supervisors who allow emails (default to True if None)
    supervisor_emails = [s.email for s in supervisors if s.email_allowed is not False]

    if supervisor_emails:
        admin_url = url_for("admin.manage_signups", _external=True)
        send_email(
            "[MECWS] New Volunteer Signup",
            current_app.config["MAIL_DEFAULT_SENDER"],
            supervisor_emails,
            render_template(
                "email/new_signup.txt", user=current_user, shift=shift, url=admin_url
            ),
            render_template(
                "email/new_signup.html", user=current_user, shift=shift, url=admin_url
            ),
        )

    # Notify Volunteer of Pending Status
    if current_user.email_allowed is not False:
        send_email(
            "[MECWS] Signup Pending",
            current_app.config["MAIL_DEFAULT_SENDER"],
            [current_user.email],
            render_template("email/signup_pending.txt", user=current_user, shift=shift),
            render_template("email/signup_pending.html", user=current_user, shift=shift),
        )

    flash("Signup requested! Waiting for supervisor confirmation.", "success")
    return redirect(url_for("volunteer.my_schedule"))


@volunteer_bp.route("/my-schedule")
@login_required
def my_schedule():
    my_signups = (
        Signup.query.join(Shift)
        .join(Event)
        .filter(Signup.user_id == current_user.id)
        .order_by(Event.date)
        .all()
    )
    return render_template("volunteer/my_schedule.html", signups=my_signups)


@volunteer_bp.route("/signup/<int:signup_id>/cancel", methods=["POST"])
@login_required
def cancel_signup(signup_id):
    signup = Signup.query.get_or_404(signup_id)

    # Ensure ownership
    if signup.user_id != current_user.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("volunteer.my_schedule"))

    # Ensure status is pending
    if signup.confirmed:
        flash("Cannot cancel a confirmed shift. Please contact a supervisor.", "danger")
        return redirect(url_for("volunteer.my_schedule"))

    # Delete (Cancel)
    db.session.delete(signup)
    db.session.commit()

    flash("Signup cancelled successfully.", "info")
    return redirect(url_for("volunteer.my_schedule"))
