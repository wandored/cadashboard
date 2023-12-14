"""
Dashboard App
"""

from asgiref.wsgi import WsgiToAsgi
from flask import Flask
from importlib import import_module
from dashapp.authentication.models import db, admin, security, user_datastore, mail
from dashapp.config import Config


def register_extensions(app):
    db.init_app(app)
    mail.init_app(app)
    admin.init_app(app)
    security.init_app(app, user_datastore)


def register_blueprints(app):
    for module_name in ("authentication", "home", "purchasing", "supply"):
        module = import_module("dashapp.{}.routes".format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):
    with app.app_context():
        db.reflect()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    #    asgi_app = WsgiToAsgi(app) # added for uvicorn
    return app
