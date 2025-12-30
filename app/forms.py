from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    BooleanField,
    widgets,
)
from wtforms.validators import DataRequired


class EventForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[("planned", "Planned"), ("active", "Active")],
        default="planned",
    )
    submit = SubmitField("Create Event")


class VisitorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    alias = StringField("Alias (Optional)")
    submit = SubmitField("Register Visitor")


class TeamMemberForm(FlaskForm):
    name = StringField("Name")
    email = StringField("Email Address", validators=[DataRequired()])
    phone_number = StringField("Phone Number")
    emergency_contact = StringField("Emergency Contact")
    role = SelectField(
        "Role",
        choices=[
            ("Team Member", "Team Member"),
            ("Shelter Supervisor", "Shelter Supervisor"),
        ],
    )
    level = SelectField(
        "Experience Level",
        choices=[
            ("Beginner", "Beginner"),
            ("Intermediate", "Intermediate"),
            ("Advanced", "Advanced"),
        ],
    )
    shift_preference = SelectMultipleField(
        "Shift Preference",
        choices=[
            ("7:45PM-12AM", "7:45PM - 12:00AM"),
            ("12AM-4AM", "12:00AM - 4:00AM"),
            ("4AM-8AM", "4:00AM - 8:00AM"),
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False),
    )
    email_allowed = BooleanField('Email Notifications Allowed', default=True)
    submit = SubmitField("Update Member")


class ProfileForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    phone_number = StringField("Phone Number")
    emergency_contact = StringField("Emergency Contact")
    shift_preference = SelectMultipleField(
        "Shift Preference",
        choices=[
            ("7:45PM-12AM", "7:45PM - 12:00AM"),
            ("12AM-4AM", "12:00AM - 4:00AM"),
            ("4AM-8AM", "4:00AM - 8:00AM"),
        ],
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False),
    )
    email_allowed = BooleanField('Receive Email Notifications', default=True)
    submit = SubmitField("Update Profile")


class AssignVolunteerForm(FlaskForm):
    user_id = SelectField("Team Member", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Assign")


class EmailTemplateForm(FlaskForm):
    slug = StringField("Slug (Unique Identifier)", validators=[DataRequired()])
    name = StringField("Template Name", validators=[DataRequired()])
    subject = StringField("Subject Line", validators=[DataRequired()])
    body_text = TextAreaField("Plain Text Body")
    body_html = TextAreaField("HTML Body")
    submit = SubmitField("Save Template")


class BroadcastEmailForm(FlaskForm):
    subject = StringField("Subject", validators=[DataRequired()])
    message = TextAreaField("Message", validators=[DataRequired()], description="Use {{ name }} for volunteer name and {{ date }} for event date.")
    submit = SubmitField("Send Email")
