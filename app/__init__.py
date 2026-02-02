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

    # Initialize Session
    app.config["SESSION_SQLALCHEMY"] = db
    from flask_session import Session
    Session(app)

    login_manager.login_view = "main.login"

    # Register Blueprints
    from app.routes.admin import admin_bp
    from app.routes.main import main_bp
    from app.routes.visitor import visitor_bp
    from app.routes.volunteer import volunteer_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(volunteer_bp)
    app.register_blueprint(visitor_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_templates():
        from app.models import EmailTemplate
        from markupsafe import Markup

        class TemplateWrapper:
            def __init__(self, slug):
                self.slug = slug
                self._tmpl = None
            
            @property
            def tmpl(self):
                if self._tmpl is None:
                    self._tmpl = EmailTemplate.query.filter_by(slug=self.slug).first()
                return self._tmpl

            @property
            def html(self):
                if not self.tmpl or not self.tmpl.body_html:
                    return ""
                # Render the content as a template to process variables like {{ unsubscribe_url }}
                # Note: The context variables must be available in the parent template render context.
                from flask import render_template_string
                return Markup(render_template_string(self.tmpl.body_html))

            @property
            def text(self):
                if not self.tmpl or not self.tmpl.body_text:
                    return ""
                from flask import render_template_string
                return render_template_string(self.tmpl.body_text)
            
            def __getattr__(self, name):
                return getattr(self.tmpl, name) if self.tmpl else None
            
            def __str__(self):
                return self.text

        class TemplateLoader:
            def __getitem__(self, key):
                return TemplateWrapper(key)
            
            def __getattr__(self, key):
                return TemplateWrapper(key)

        return dict(template=TemplateLoader())

    return app
