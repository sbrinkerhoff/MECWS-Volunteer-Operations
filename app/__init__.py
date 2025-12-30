from flask import Flask

from app.config import Config
from app.extensions import bootstrap, db, login_manager, mail, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    bootstrap.init_app(app)
    mail.init_app(app)

    login_manager.login_view = "main.login"

    # Register Blueprints
    from app.routes.admin import admin_bp
    from app.routes.main import main_bp
    from app.routes.visitor import visitor_bp
    from app.routes.volunteer import volunteer_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(volunteer_bp)
    app.register_blueprint(visitor_bp)

    return app
