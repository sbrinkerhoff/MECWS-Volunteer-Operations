from app import create_app


def test_email_configuration_loaded():
    """Test that email configuration is correctly loaded from .env"""
    # Force load dotenv if not already loaded by the test runner's environment
    from dotenv import load_dotenv

    load_dotenv()

    app = create_app()

    assert app.config["MAIL_SERVER"] == "smtp-relay.brevo.com"
    assert app.config["MAIL_PORT"] == 587
    assert app.config["MAIL_USE_TLS"] is True
    assert app.config["MAIL_USERNAME"] == "stan@vtwireless.com"
    # We won't test the password content for security logging, but check it exists
    assert app.config["MAIL_PASSWORD"] is not None
    assert "coordinator@mecws.org" in app.config["MAIL_DEFAULT_SENDER"]
