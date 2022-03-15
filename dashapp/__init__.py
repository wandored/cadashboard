"""
CentraArchy Dashboard App
"""

from flask import Flask
from importlib import import_module
from dashapp.authentication.models import db, admin, security, user_datastore, mail
from dashapp.config import Config


def register_extensions(app):
    db.init_app(app)
    mail.init_app(app)
    #    login_manager.init_app(app)
    admin.init_app(app)
    security.init_app(app, user_datastore)


def register_blueprints(app):
    for module_name in ("authentication", "home"):
        module = import_module("dashapp.{}.routes".format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):
    @app.before_first_request
    def initialize_database():
        db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    return app
