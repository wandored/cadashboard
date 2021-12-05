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
    SECURITY_CHANGEABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_PASSWORD_SALT = 'verysalty'
    SECURITY_SEND_REGISTER_EMAIL = True
    SECURITY_EMAIL_SUBJECT_REGISTER = "CentraArchy Dashboard Registration"
    SECURITY_EMAIL_SENDER = "Support@centraarchy.com"
    MAIL_USERNAME = config.get('EMAIL_USER')
    MAIL_PASSWORD = config.get('EMAIL_PASS')
    MAIL_SERVER = config.get("EMAIL_SERVER")
    MAIL_PORT = config.get("EMAIL_PORT")
    MAIL_DEFAULT_SENDER = config.get("MAIL_DEFAULT_SENDER")
    HOST_SERVER = config.get("HOST_SERVER")

