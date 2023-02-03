import json

with open("/etc/config.json") as config_file:
    config = json.load(config_file)


class Config:
    COMPANY_NAME = config.get("COMPANY_NAME")
    SECRET_KEY = config.get("SECRET_KEY")
    SRVC_ROOT = config.get("SRVC_ROOT")
    SRVC_USER = config.get("SRVC_USER")
    SRVC_PSWRD = config.get("SRVC_PSWRD")
    SQLALCHEMY_DATABASE_URI = config.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = config.get("SQLALCHEMY_TRACK_MODIFICATIONS")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_MAX_OVERFLOW = 20
    SQLALCHEMY_POOL_RECYCLE = 1800
    SECURITY_REGISTERABLE = config.get("SECURITY_REGISTERABLE")
    SECURITY_CHANGEABLE = config.get("SECURITY_CHANGEABLE")
    SECURITY_RECOVERABLE = config.get("SECURITY_RECOVERABLE")
    SECURITY_PASSWORD_SALT = config.get("SECURITY_PASSWORD_SALT")
    SECURITY_EMAIL_SUBJECT_REGISTER = config.get("SECURITY_EMAIL_SUBJECT_REGISTER")
    SECURITY_EMAIL_SENDER = config.get("SECURITY_EMAIL_SENDER")
    SECURITY_DEFAULT_REMEMBER_ME = config.get("SECURITY_DEFAULT_REMEMBER_ME")
    SECURITY_FLASH_MESSAGES = config.get("SECURITY_FLASH_MESSAGES")
    MAIL_USERNAME = config.get("EMAIL_USER")
    MAIL_PASSWORD = config.get("EMAIL_PASS")
    MAIL_SERVER = config.get("EMAIL_SERVER")
    MAIL_PORT = config.get("EMAIL_PORT")
    MAIL_USE_SSL = config.get("EMAIL_USE_SSL")
    MAIL_DEFAULT_SENDER = config.get("MAIL_DEFAULT_SENDER")
    HOST_SERVER = config.get("HOST_SERVER")
    PSYCOPG2_USER = config.get("PSYCOPG2_USER")
    PSYCOPG2_PASS = config.get("PSYCOPG2_PASS")
