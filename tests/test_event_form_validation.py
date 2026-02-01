
import pytest
from app.forms import EventForm
from app import create_app
from datetime import date
from werkzeug.datastructures import MultiDict

@pytest.fixture
def app():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    return app

def test_event_date_validation(app):
    with app.app_context(), app.test_request_context():
        # Valid date
        # Passing formdata to parse strings
        form = EventForm(formdata=MultiDict({'date': '2025-01-01', 'status': 'projected'}))
        assert form.validate(), f"Validation failed: {form.errors}"

        # Invalid date (2020)
        form = EventForm(formdata=MultiDict({'date': '2020-12-31', 'status': 'projected'}))
        assert not form.validate()
        assert "Event date must be after 2020." in form.date.errors

        # Invalid date (2019)
        form = EventForm(formdata=MultiDict({'date': '2019-01-01', 'status': 'projected'}))
        assert not form.validate()
        assert "Event date must be after 2020." in form.date.errors
