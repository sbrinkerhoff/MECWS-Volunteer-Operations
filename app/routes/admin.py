from datetime import time

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.forms import AssignVolunteerForm, EventForm, TeamMemberForm
from app.models import Event, Shift, Signup, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def require_supervisor():
    if current_user.role != "Shelter Supervisor":
        flash("Access denied. Supervisor privileges required.", "danger")
        return redirect(url_for("main.dashboard"))


@admin_bp.route("/events")
def list_events():
    events = Event.query.order_by(Event.date.desc()).all()
    return render_template("admin/list_events.html", events=events)


@admin_bp.route("/events/new", methods=["GET", "POST"])
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(date=form.date.data, status=form.status.data)
        db.session.add(event)

        # Create standard shifts
        shifts = [
            Shift(start_time=time(19, 45), end_time=time(0, 0), event=event),
            Shift(start_time=time(0, 0), end_time=time(4, 0), event=event),
            Shift(start_time=time(4, 0), end_time=time(8, 0), event=event),
        ]

        for shift in shifts:
            db.session.add(shift)

        db.session.commit()
        flash("Event and standard shifts created successfully.", "success")
        return redirect(url_for("admin.list_events"))

    # Fetch weather for guidance
    from app.weather import get_weather_calendar

    weather_calendar = get_weather_calendar()

    return render_template(
        "admin/create_event.html", form=form, weather_calendar=weather_calendar
    )


@admin_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = EventForm(obj=event)

    if form.validate_on_submit():
        event.date = form.date.data
        event.status = form.status.data
        db.session.commit()
        flash("Event updated successfully.", "success")
        return redirect(url_for("admin.list_events"))

    return render_template("admin/create_event.html", form=form, title="Edit Event")


@admin_bp.route("/events/<int:event_id>/delete", methods=["POST"])
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.", "success")
    return redirect(url_for("admin.list_events"))


@admin_bp.route("/events/<int:event_id>")
def view_event(event_id):
    event = Event.query.get_or_404(event_id)

    # Form for assigning volunteers
    assign_form = AssignVolunteerForm()
    assign_form.user_id.choices = [
        (u.id, f"{u.name} <{u.email}>" if u.name else u.email)
        for u in User.query.order_by(User.name).all()
    ]

    # Visitors logic
    from app.models import Visitor

    visitors = Visitor.query.order_by(Visitor.name).all()

    return render_template(
        "admin/view_event.html", event=event, assign_form=assign_form, visitors=visitors
    )


@admin_bp.route("/events/<int:event_id>/checkin", methods=["POST"])
def checkin_visitor(event_id):
    event = Event.query.get_or_404(event_id)
    visitor_name = request.form.get("visitor_name")

    if not visitor_name:
        flash("Visitor name is required.", "warning")
        return redirect(url_for("admin.view_event", event_id=event_id))

    from app.models import CheckIn, Visitor

    # 1. Try to find existing visitor by exact name (case insensitive ideally, but sqlite is default case insensitive for ascii)
    visitor = Visitor.query.filter(Visitor.name.ilike(visitor_name)).first()

    if not visitor:
        # Create new visitor
        visitor = Visitor(
            name=visitor_name, alias=visitor_name
        )  # Default alias to name
        db.session.add(visitor)
        db.session.commit()
        flash(f"Created new visitor profile for {visitor_name}.", "info")

    # 2. Check overlap
    existing_checkin = CheckIn.query.filter_by(
        event_id=event_id, visitor_id=visitor.id
    ).first()
    if existing_checkin:
        flash(f"{visitor.name} is already checked in.", "warning")
    else:
        checkin = CheckIn(event_id=event_id, visitor_id=visitor.id)
        db.session.add(checkin)
        db.session.commit()
        flash(f"Checked in {visitor.name} successfully.", "success")

    return redirect(url_for("admin.view_event", event_id=event_id))


@admin_bp.route("/shifts/<int:shift_id>/assign", methods=["POST"])
def assign_volunteer(shift_id):
    shift = Shift.query.get_or_404(shift_id)

    # We are getting a text identifier now: "John Doe <john@example.com>" or similar
    # We need to find the ID.
    identifier = request.form.get("user_identifier")

    # Try to extract email from "Name <email>" format strictly first, or fuzzy match name
    import re

    email_match = re.search(r"<([^>]+)>", identifier)
    user = None

    if email_match:
        email = email_match.group(1)
        user = User.query.filter_by(email=email).first()
    else:
        # User might have typed just "Name" or "Email"
        # 1. Exact Email Match
        user = User.query.filter_by(email=identifier).first()

        # 2. Exact Name Match
        if not user:
            user = User.query.filter_by(name=identifier).first()

        # 3. Fuzzy Search (if they typed 'John' and 'John <john@example.com>' exists)
        # Note: This might be ambiguous if multiple Johns, but better than failing.
        # Ideally, we require selection from the dropdown which populates the full format.
        if not user:
            # Check if the identifier matches the start of a name or email
            user = User.query.filter(
                (User.name.ilike(f"{identifier}%"))
                | (User.email.ilike(f"{identifier}%"))
            ).first()

    if not user:
        flash("Could not find a user matching that name/email.", "danger")
        return redirect(url_for("admin.view_event", event_id=shift.event_id))

    user_id = user.id

    # Check if already signed up
    existing = Signup.query.filter_by(user_id=user_id, shift_id=shift_id).first()
    if existing:
        flash("User is already assigned to this shift.", "warning")
    else:
        signup = Signup(user_id=user_id, shift_id=shift_id, confirmed=True)
        db.session.add(signup)
        db.session.commit()
        flash(f"Volunteer {user.name or user.email} assigned successfully.", "success")

    return redirect(url_for("admin.view_event", event_id=shift.event_id))


@admin_bp.route("/signups/<int:signup_id>/remove", methods=["POST"])
def remove_signup(signup_id):
    signup = Signup.query.get_or_404(signup_id)
    event_id = signup.shift.event_id
    db.session.delete(signup)
    db.session.commit()
    flash("Volunteer removed from shift.", "info")
    return redirect(url_for("admin.view_event", event_id=event_id))


@admin_bp.route("/signups")
def manage_signups():
    # Get all pending signups
    pending_signups = (
        Signup.query.filter_by(confirmed=False)
        .join(Shift)
        .join(Event)
        .order_by(Event.date)
        .all()
    )
    return render_template("admin/manage_signups.html", signups=pending_signups)


@admin_bp.route("/signups/confirm/<int:signup_id>", methods=["POST"])
def confirm_signup(signup_id):
    signup = Signup.query.get_or_404(signup_id)
    signup.confirmed = True
    db.session.commit()

    # Mock Notification
    # print(f"NOTIFICATION SENT TO {signup.volunteer.email}: Your signup for {signup.shift.event.date} has been CONFIRMED.")

    from flask import current_app

    from app.email import send_email

    send_email(
        "[MECWS] Signup Confirmed",
        current_app.config["MAIL_DEFAULT_SENDER"],
        [signup.volunteer.email],
        render_template(
            "email/signup_confirmed.txt", user=signup.volunteer, shift=signup.shift
        ),
        render_template(
            "email/signup_confirmed.html", user=signup.volunteer, shift=signup.shift
        ),
    )

    flash(f"Signup for {signup.volunteer.email} confirmed.", "success")
    return redirect(url_for("admin.manage_signups"))


@admin_bp.route("/signups/reject/<int:signup_id>", methods=["POST"])
def reject_signup(signup_id):
    signup = Signup.query.get_or_404(signup_id)
    email = signup.volunteer.email
    db.session.delete(signup)
    db.session.commit()

    flash(f"Signup for {email} rejected.", "info")
    return redirect(url_for("admin.manage_signups"))


@admin_bp.route("/team")
def manage_team():
    query = request.args.get("q", "")
    if query:
        # Search by Name or Email
        users = (
            User.query.filter(
                (User.email.ilike(f"%{query}%")) | (User.name.ilike(f"%{query}%"))
            )
            .order_by(User.role, User.email)
            .all()
        )
    else:
        users = User.query.order_by(User.role, User.email).all()

    return render_template("admin/list_team.html", users=users, search_query=query)


@admin_bp.route("/team/new", methods=["GET", "POST"])
def add_team_member():
    form = TeamMemberForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash(f"User with email {form.email.data} already exists.", "warning")
            return redirect(url_for("admin.add_team_member"))

        user = User(
            name=form.name.data,
            email=form.email.data,
            phone_number=form.phone_number.data,
            emergency_contact=form.emergency_contact.data,
            role=form.role.data,
            level=form.level.data,
            shift_preference=",".join(form.shift_preference.data),
            email_allowed=form.email_allowed.data
        )
        db.session.add(user)
        db.session.commit()

        flash(f"Team member {user.email} created successfully.", "success")
        return redirect(url_for("admin.manage_team"))

    return render_template("admin/add_team_member.html", form=form)


@admin_bp.route("/team/<int:user_id>/edit", methods=["GET", "POST"])
def edit_team_member(user_id):
    user = User.query.get_or_404(user_id)
    form = TeamMemberForm(obj=user)

    # Pre-process stored string to list for form population (GET)
    if request.method == "GET" and user.shift_preference:
        form.shift_preference.data = user.shift_preference.split(",")

    if form.validate_on_submit():
        user.name = form.name.data
        user.email = form.email.data
        user.phone_number = form.phone_number.data
        user.emergency_contact = form.emergency_contact.data
        user.role = form.role.data
        user.level = form.level.data
        user.email_allowed = form.email_allowed.data

        # Convert list back to string for storage
        user.shift_preference = ",".join(form.shift_preference.data)

        db.session.commit()
        flash(f"Team member {user.email} updated successfully.", "success")
        return redirect(url_for("admin.manage_team"))

    return render_template("admin/edit_team_member.html", form=form, user=user)


@admin_bp.route("/emails")
def list_emails():
    from app.models import Email

    emails = Email.query.order_by(Email.created_at.desc()).all()
    return render_template("admin/list_emails.html", emails=emails)


@admin_bp.route("/emails/<int:email_id>")
def view_email(email_id):
    from app.models import Email

    email = Email.query.get_or_404(email_id)
    return render_template("admin/view_email.html", email=email)


@admin_bp.route("/templates")
def list_templates():
    from app.models import EmailTemplate

    templates = EmailTemplate.query.order_by(EmailTemplate.name).all()
    return render_template("admin/list_templates.html", templates=templates)


@admin_bp.route("/templates/new", methods=["GET", "POST"])
def create_template():
    from app.forms import EmailTemplateForm
    from app.models import EmailTemplate

    form = EmailTemplateForm()
    if form.validate_on_submit():
        if EmailTemplate.query.filter_by(slug=form.slug.data).first():
            flash("Template with this slug already exists.", "warning")
        else:
            template = EmailTemplate(
                slug=form.slug.data,
                name=form.name.data,
                subject=form.subject.data,
                body_text=form.body_text.data,
                body_html=form.body_html.data,
            )
            db.session.add(template)
            db.session.commit()
            flash("Email template created successfully.", "success")
            return redirect(url_for("admin.list_templates"))

    return render_template(
        "admin/edit_template.html", form=form, title="Create Template"
    )


@admin_bp.route("/templates/<int:template_id>/edit", methods=["GET", "POST"])
def edit_template(template_id):
    from app.forms import EmailTemplateForm
    from app.models import EmailTemplate

    template = EmailTemplate.query.get_or_404(template_id)
    form = EmailTemplateForm(obj=template)

    if form.validate_on_submit():
        # Check unique slug if changed
        existing = EmailTemplate.query.filter_by(slug=form.slug.data).first()
        if existing and existing.id != template.id:
            flash("Template with this slug already exists.", "warning")
        else:
            template.slug = form.slug.data
            template.name = form.name.data
            template.subject = form.subject.data
            template.body_text = form.body_text.data
            template.body_html = form.body_html.data

            db.session.commit()
            flash("Email template updated successfully.", "success")
            return redirect(url_for("admin.list_templates"))

    return render_template("admin/edit_template.html", form=form, title="Edit Template")


@admin_bp.route("/templates/<int:template_id>/delete", methods=["POST"])
def delete_template(template_id):
    from app.models import EmailTemplate

    template = EmailTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    flash("Template deleted.", "info")
    return redirect(url_for("admin.list_templates"))


@admin_bp.route("/events/<int:event_id>/broadcast", methods=["GET", "POST"])
def broadcast_email(event_id):
    from app.forms import BroadcastEmailForm
    from flask import current_app
    from app.email import send_email

    event = Event.query.get_or_404(event_id)
    form = BroadcastEmailForm()

    if request.method == "GET":
        form.subject.data = f"Volunteers Needed: {event.date.strftime('%A, %B %d')}"
        form.message.data = (
            "Hi {{ name }},\n\n"
            "We are activating the shelter for {{ date }}. "
            "We still have open shifts and would appreciate your help.\n\n"
            "Please click the link below to sign up:\n"
            "{{ link }}\n\n"
            "Thanks,\nMECWS Team"
        )

    if form.validate_on_submit():
        # Get all team members who allow emails
        # Filter where email_allowed is True or None (legacy)
        users = User.query.filter(User.role == "Team Member").all()
        recipients = [u for u in users if u.email_allowed is not False]
        
        # Pre-import for loop
        import uuid
        from app.models import LoginToken
        from datetime import datetime, timedelta
        
        count = 0
        for user in recipients:
            # Generate Login Token for user
            token_str = str(uuid.uuid4())
            expiry = datetime.utcnow() + timedelta(days=2) # 48 hour link for broadcast
            token_entry = LoginToken(token=token_str, user_id=user.id, expires_at=expiry)
            db.session.add(token_entry)
            
            # Create Magic Link with redirect
            # We want them to go to available shifts
            magic_link = url_for("main.validate_magic_link", token=token_str, next=url_for('volunteer.available_shifts'), _external=True, _scheme='https')

            # Replace variables
            message = form.message.data
            message = message.replace("{{ name }}", user.name or "Team Member")
            message = message.replace("{{ date }}", event.date.strftime('%B %d, %Y'))
            message = message.replace("{{ link }}", magic_link)
            
            # Send (Simple text body for now, could enhance to HTML)
            # Basic HTML conversion
            html_body = f"<p>{message.replace(chr(10), '<br>')}</p>"
            # Make link clickable in HTML
            if magic_link in message:
                 html_body = html_body.replace(magic_link, f'<a href="{magic_link}">Click here to sign up</a>')
            
            send_email(
                f"[MECWS] {form.subject.data}",
                current_app.config["MAIL_DEFAULT_SENDER"],
                [user.email],
                message,
                html_body
            )
            count += 1
            
        db.session.commit() # Commit all tokens
        flash(f"Broadcast sent to {count} volunteers.", "success")
        return redirect(url_for("admin.view_event", event_id=event.id))

    return render_template("admin/broadcast_email.html", form=form, event=event)
