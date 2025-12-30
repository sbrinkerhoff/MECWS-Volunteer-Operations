from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.forms import VisitorForm
from app.models import CheckIn, Event, Visitor, db

visitor_bp = Blueprint("visitor", __name__, url_prefix="/visitors")


@visitor_bp.before_request
@login_required
def require_supervisor():
    if current_user.role != "Shelter Supervisor":
        flash("Access denied. Supervisor privileges required.", "danger")
        return redirect(url_for("main.dashboard"))


@visitor_bp.route("/")
@login_required
def list_visitors():
    visitors = Visitor.query.order_by(Visitor.name).all()
    # Find today's event for check-in context
    from datetime import date

    today_event = Event.query.filter_by(date=date.today()).first()
    return render_template(
        "visitor/list_visitors.html", visitors=visitors, today_event=today_event
    )


@visitor_bp.route("/checkin/<int:visitor_id>/<int:event_id>", methods=["POST"])
@login_required
def check_in(visitor_id, event_id):
    checkin = CheckIn(visitor_id=visitor_id, event_id=event_id)
    db.session.add(checkin)
    db.session.commit()

    visitor = Visitor.query.get(visitor_id)
    flash(f"Checked in {visitor.name} for tonight.", "success")
    return redirect(url_for("visitor.list_visitors"))


@visitor_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_visitor():
    form = VisitorForm()
    if form.validate_on_submit():
        visitor = Visitor(name=form.name.data, alias=form.alias.data)
        db.session.add(visitor)
        db.session.commit()
        flash(f"Visitor {visitor.name} registered successfully.", "success")
        return redirect(url_for("visitor.list_visitors"))

    return render_template(
        "visitor/create_visitor.html", form=form, title="Register Visitor"
    )


@visitor_bp.route("/<int:visitor_id>/edit", methods=["GET", "POST"])
@login_required
def edit_visitor(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    form = VisitorForm(obj=visitor)

    if form.validate_on_submit():
        visitor.name = form.name.data
        visitor.alias = form.alias.data
        db.session.commit()
        flash(f"Visitor {visitor.name} updated successfully.", "success")
        return redirect(url_for("visitor.list_visitors"))

    return render_template(
        "visitor/create_visitor.html", form=form, title="Edit Visitor"
    )
