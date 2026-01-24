from flask import Flask

from app.config import Config
from app.extensions import bootstrap, db, login_manager, mail, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    import logging
    from logging.handlers import RotatingFileHandler
    import os

    if not app.debug and not app.testing:
        # In production, we might want cleaner output, but here we setup specific
        # logging for application events regardless of debug mode, or just for production.
        # Let's configure a specific logger or attach to app.logger
        pass

    # Basic File Logging config
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler('logs/mecws.log', maxBytes=1024 * 1024, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('MECWS startup')


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
