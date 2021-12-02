import json

with open("/etc/config.json") as config_file:
    config = json.load(config_file)


class Config:
    SECRET_KEY = config.get("SECRET_KEY")
    SRVC_ROOT = config.get("SRVC_ROOT")
    SRVC_USER = config.get("SRVC_USER")
    SRVC_PSWRD = config.get("SRVC_PSWRD")
    SQLALCHEMY_DATABASE_URI = config.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECURITY_REGISTERABLE = True
    SECURITY_PASSWORD_SALT = 'verysalty'
    SECURITY_SEND_REGISTER_EMAIL = False
    EMAIL_USER = config.get('EMAIL_USER')
    EMAIL_PASS = config.get("EMAIL_PASS")
    EMAIL_SERVER = config.get("EMAIL_SERVER")
    EMAIL_PORT = config.get("EMAIL_PORT")
    MAIL_DEFAULT_SENDER = config.get("MAIL_DEFAULT_SENDER")
    HOST_SERVER = config.get("HOST_SERVER")

