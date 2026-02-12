from datetime import time

from flask import Blueprint, flash, redirect, render_template, request, url_for, send_file
from flask_login import current_user, login_required
import pandas as pd
from io import BytesIO

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
    events = Event.query.all()
    
    active_statuses = ['projected', 'confirmed']
    # Filter for active events (projected/confirmed) and sort by date ascending (soonest first)
    active_events = sorted(
        [e for e in events if e.status in active_statuses],
        key=lambda x: x.date
    )
    
    # Filter for inactive events (completed/cancelled) and sort by date descending (newest first)
    inactive_events = sorted(
        [e for e in events if e.status not in active_statuses],
        key=lambda x: x.date,
        reverse=True
    )

    return render_template("admin/list_events.html", active_events=active_events, inactive_events=inactive_events)


@admin_bp.route("/events/new", methods=["GET", "POST"])
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(date=form.date.data, status=form.status.data, description=form.description.data, notify_coordinators=form.notify_coordinators.data)
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
        
        from app.audit import log_audit
        log_audit("create_event", f"Created event for {event.date} with status {event.status}")
        
        flash("Event and standard shifts created successfully.", "success")
        return redirect(url_for("admin.list_events"))

    # Fetch weather for guidance
    from app.weather import get_weather_calendar

    weather_calendar = get_weather_calendar()

    from flask import current_app
    lat = current_app.config["WEATHER_LAT"]
    lon = current_app.config["WEATHER_LON"]
    weather_url = f"https://forecast.weather.gov/MapClick.php?lat={lat}&lon={lon}"

    return render_template(
        "admin/create_event.html", form=form, weather_calendar=weather_calendar, weather_url=weather_url
    )


@admin_bp.route("/events/<event_id>/edit", methods=["GET", "POST"])
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = EventForm(obj=event)

    if form.validate_on_submit():
        event.date = form.date.data
        event.status = form.status.data
        event.description = form.description.data
        event.notify_coordinators = form.notify_coordinators.data
        db.session.commit()
        flash("Event updated successfully.", "success")
        return redirect(url_for("admin.list_events"))

    return render_template("admin/create_event.html", form=form, title="Edit Event")


@admin_bp.route("/events/<event_id>/update_meta", methods=["POST"])
def update_event_meta(event_id):
    event = Event.query.get_or_404(event_id)
    
    date_str = request.form.get("date")
    status = request.form.get("status")
    description = request.form.get("description")
    notify = request.form.get("notify_coordinators") == "on"
    
    from datetime import datetime
    try:
        if date_str:
            event.date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return redirect(url_for("admin.view_event", event_id=event_id))
        
    if status:
        event.status = status
        
    event.description = description
    event.notify_coordinators = notify
    
    db.session.commit()
    
    from app.audit import log_audit
    log_audit("update_event", f"Updated metadata for {event.date}", user=current_user)
    
    flash("Event updated successfully.", "success")
    return redirect(url_for("admin.view_event", event_id=event_id))


@admin_bp.route("/events/<event_id>/cancel", methods=["POST"])
def cancel_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.status = "cancelled"
    db.session.commit()
    
    from app.audit import log_audit
    log_audit("cancel_event", f"Cancelled event for {event.date}", user=current_user)
    
    flash("Event cancelled successfully.", "success")
    return redirect(url_for("admin.list_events"))


@admin_bp.route("/events/<event_id>")
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


@admin_bp.route("/events/<event_id>/checkin", methods=["POST"])
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


@admin_bp.route("/shifts/<shift_id>/assign", methods=["POST"])
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
        # Default to True validation if checked or field missing (legacy behavior was always true)
        # But we want to allow unconfirmed. 
        # If 'confirmed' is in form (checkbox), use its value.
        # The form will have <input type="checkbox" name="confirmed" checked>
        # The checkbox will send "on" if checked. If unchecked, the key is missing.
        is_confirmed = request.form.get("confirmed") == "on"
        # If the form field is missing (e.g. old forms), we might assume True to be safe/backward compatible, 
        # or we update the form everywhere. 
        # Since I am updating the only form that calls this, I will rely on the field.
        # But to be safe: default to True if we aren't sure.
        
        signup = Signup(user_id=user_id, shift_id=shift_id, confirmed=is_confirmed)
        db.session.add(signup)
        db.session.commit()
        
        if is_confirmed:
            flash(f"Volunteer {user.name or user.email} assigned successfully.", "success")
        else:
            flash(f"Volunteer {user.name or user.email} added (awaiting confirmation).", "info")

    return redirect(url_for("admin.view_event", event_id=shift.event_id))


@admin_bp.route("/signups/<signup_id>/remove", methods=["GET", "POST"])
def remove_signup(signup_id):
    signup = Signup.query.get_or_404(signup_id)
    event_id = signup.shift.event_id
    
    if request.method == "GET":
        return render_template(
            "admin/confirm_remove_volunteer.html",
            signup=signup,
            action_url=url_for("admin.remove_signup", signup_id=signup_id),
            cancel_url=url_for("admin.view_event", event_id=event_id)
        )
    
    # POST handling
    notify = request.form.get("notify") == "true"
    custom_message = request.form.get("custom_message")
    
    if notify and signup.volunteer.email_allowed is not False:
        from flask import current_app
        from app.email import send_email
        
        send_email(
            "[MECWS] Schedule Update",
            current_app.config["MAIL_DEFAULT_SENDER"],
            [signup.volunteer.email],
            render_template("email/signup_removed.txt", user=signup.volunteer, shift=signup.shift, custom_message=custom_message),
            render_template("email/signup_removed.html", user=signup.volunteer, shift=signup.shift, custom_message=custom_message),
        )

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


@admin_bp.route("/signups/confirm/<signup_id>", methods=["POST"])
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
    
    next_url = request.args.get("next")
    if next_url:
        return redirect(next_url)
        
    return redirect(url_for("admin.manage_signups"))


@admin_bp.route("/signups/reject/<signup_id>", methods=["POST"])
def reject_signup(signup_id):
    signup = Signup.query.get_or_404(signup_id)
    email = signup.volunteer.email
    db.session.delete(signup)
    db.session.commit()

    flash(f"Signup for {email} rejected.", "info")
    
    next_url = request.args.get("next")
    if next_url:
        return redirect(next_url)
        
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
            address_street=form.address_street.data,
            address_city=form.address_city.data,
            address_state=form.address_state.data,
            emergency_contact=form.emergency_contact.data,
            role=form.role.data,
            level=form.level.data,
            shift_preference=",".join(form.shift_preference.data),
            email_allowed=form.email_allowed.data
        )
        db.session.add(user)
        db.session.commit()

        from app.audit import log_audit
        log_audit("create_user", f"Created team member {user.email}", user=current_user)

        flash(f"Team member {user.email} created successfully.", "success")
        return redirect(url_for("admin.manage_team"))

    return render_template("admin/add_team_member.html", form=form)


@admin_bp.route("/team/<user_id>/edit", methods=["GET", "POST"])
def edit_team_member(user_id):
    user = User.query.get_or_404(user_id)
    form = TeamMemberForm(obj=user)

    # Pre-process stored string to list for form population (GET)
    if request.method == "GET" and user.shift_preference:
        form.shift_preference.data = user.shift_preference.split(",")

    if form.validate_on_submit():
        # Track changes
        changes = []
        
        # Helper to check and update
        def update_field(field_name, new_value, label):
            old_value = getattr(user, field_name)
            # Normalize for comparison
            if old_value is None: old_value = ""
            if new_value is None: new_value = ""
            
            if str(old_value) != str(new_value):
                setattr(user, field_name, new_value if new_value != "" else None)
                changes.append(f"{label}: '{old_value}' -> '{new_value}'")

        update_field("name", form.name.data, "Name")
        update_field("email", form.email.data, "Email")
        update_field("phone_number", form.phone_number.data, "Phone")
        update_field("address_street", form.address_street.data, "Street")
        update_field("address_city", form.address_city.data, "City")
        update_field("address_state", form.address_state.data, "State")
        update_field("emergency_contact", form.emergency_contact.data, "Emergency Contact")
        update_field("role", form.role.data, "Role")
        update_field("level", form.level.data, "Level")
        update_field("notes", form.notes.data, "Notes")
        update_field("email_allowed", form.email_allowed.data, "Email Allowed")

        # Special handling for shift preference list
        new_prefs = ",".join(form.shift_preference.data) if form.shift_preference.data else ""
        old_prefs = user.shift_preference or ""
        if old_prefs != new_prefs:
             user.shift_preference = new_prefs
             changes.append(f"Mac Prefs: '{old_prefs}' -> '{new_prefs}'")

        if changes:
            db.session.commit()
            from app.audit import log_audit
            log_str = "; ".join(changes)
            log_audit("update_user", f"Updated {user.email}: {log_str}", user=current_user)
            flash(f"Team member updated successfully.", "success")
        else:
            flash(f"No changes made to {user.email}.", "info")
            
        return redirect(url_for("admin.manage_team"))

    return render_template("admin/edit_team_member.html", form=form, user=user)


@admin_bp.route("/team/<user_id>/delete", methods=["POST"])
def delete_team_member(user_id):
    user = User.query.get_or_404(user_id)
    email = user.email
    db.session.delete(user)
    db.session.commit()
    
    from app.audit import log_audit
    log_audit("delete_user", f"Deleted team member {email}", user=current_user)
    
    flash(f"Team member {email} removed.", "info")
    return redirect(url_for("admin.manage_team"))


@admin_bp.route("/team/import", methods=["GET", "POST"])
def import_team():
    from app.forms import UploadTeamForm
    form = UploadTeamForm()
    
    if form.validate_on_submit():
        file = form.file.data
        try:
            df = pd.read_excel(file)
            
            count = 0
            updated = 0
            
            for index, row in df.iterrows():
                # Case insensitive column matching using upper/lower
                row_map = {str(k).lower(): v for k, v in row.items()}
                
                email = row_map.get('email')
                if not email or pd.isna(email):
                    continue
                    
                email = str(email).strip().lower()
                
                user = User.query.filter_by(email=email).first()
                if not user:
                    user = User(email=email)
                    user.role = "Team Member"
                    db.session.add(user)
                    count += 1
                else:
                    updated += 1
                
                # Helper to safely get value
                def get_val(keys):
                    for k in keys:
                        if k in row_map and not pd.isna(row_map[k]):
                            val = row_map[k]
                            # Clean up nan/nat
                            if pd.isna(val): return None
                            return val
                    return None

                name = get_val(['name', 'full name', 'fullname'])
                if name: user.name = str(name)
                
                phone = get_val(['phone', 'phone number', 'cell'])
                if phone: user.phone_number = str(phone)
                
                role = get_val(['role', 'job title'])
                if role: user.role = str(role)

                notes = get_val(['notes', 'comments'])
                if notes: user.notes = str(notes)
                
            db.session.commit()
            
            from app.audit import log_audit
            log_audit("import_team", f"Imported {count} new, Updated {updated}", user=current_user)
            
            flash(f"Imported {count} new members and updated {updated} existing members.", "success")
            return redirect(url_for("admin.manage_team"))
            
        except Exception as e:
            flash(f"Error importing file: {e}", "danger")
            
    return render_template("admin/import_team.html", form=form)


@admin_bp.route("/team/export")
def export_team():
    users = User.query.all()
    
    data = []
    for user in users:
        data.append({
            "Name": user.name,
            "Email": user.email,
            "Phone": user.phone_number,
            "Role": user.role,
            "Level": user.level,
            "Address": user.address_street,
            "City": user.address_city,
            "State": user.address_state,
            "Emergency Contact": user.emergency_contact,
            "Notes": user.notes,
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Volunteers')
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='mecws_volunteers.xlsx'
    )


@admin_bp.route("/emails")
def list_emails():
    from app.models import Email

    emails = Email.query.order_by(Email.created_at.desc()).all()
    return render_template("admin/list_emails.html", emails=emails)


@admin_bp.route("/emails/<email_id>")
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


@admin_bp.route("/templates/<template_id>/edit", methods=["GET", "POST"])
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


@admin_bp.route("/templates/<template_id>/delete", methods=["POST"])
def delete_template(template_id):
    from app.models import EmailTemplate

    template = EmailTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    flash("Template deleted.", "info")
    return redirect(url_for("admin.list_templates"))


@admin_bp.route("/events/<event_id>/broadcast", methods=["GET", "POST"])
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


@admin_bp.route("/events/<event_id>/send_schedule", methods=["POST"])
def send_schedule(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Gather Recipient Pool
    # 1. Confirmed Volunteers on this event
    volunteers = set()
    shifts = event.shifts.all()
    
    for shift in shifts:
        for signup in shift.signups:
            if signup.confirmed and signup.volunteer.email_allowed:
                volunteers.add(signup.volunteer)
    
    # 2. All Shelter Supervisors
    supervisors = User.query.filter_by(role="Shelter Supervisor").filter(User.email_allowed != False).all()
    for sup in supervisors:
        volunteers.add(sup)
        
    recipients = [u.email for u in volunteers if u.email]
    
    if not recipients:
        flash("No recipients found (no confirmed volunteers or supervisors with email enabled).", "warning")
        return redirect(url_for("admin.view_event", event_id=event.id))
        
    from flask import current_app
    from app.email import send_email
    
    from datetime import timedelta
    
    # Sort shifts: Evening (Day 0) -> Overnight/Dawn (Day 1)
    # Logic: If starts before noon, it's next day.
    def get_sort_key(s):
        is_next_day = s.start_time.hour < 12
        return (1 if is_next_day else 0, s.start_time)

    shifts_sorted = sorted(shifts, key=get_sort_key)
    
    # Prepare data with dates for template
    shift_data = []
    for s in shifts_sorted:
        is_next_day = s.start_time.hour < 12
        s_date = event.date + timedelta(days=1) if is_next_day else event.date
        shift_data.append({
            'obj': s, 
            'date_str': s_date.strftime('%a %-m/%-d')
        })
    
    send_email(
        f"MECWS Schedule for {event.date.strftime('%a %-m/%-d')}",
        current_app.config["MAIL_DEFAULT_SENDER"],
        recipients,
        render_template("email/shift_schedule.txt", event=event, shifts=shift_data),
        render_template("email/shift_schedule.html", event=event, shifts=shift_data)
    )
    
    flash(f"Schedule sent to {len(recipients)} people.", "success")
    return redirect(url_for("admin.view_event", event_id=event.id))
