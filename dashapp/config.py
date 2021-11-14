import json
from datetime import datetime, timedelta

with open("/etc/config.json") as config_file:
    config = json.load(config_file)


class Config:
    SECRET_KEY = config.get("SECRET_KEY")
    SRVC_ROOT = config.get("SRVC_ROOT")
    SRVC_USER = config.get("SRVC_USER")
    SRVC_PSWRD = config.get("SRVC_PSWRD")
    SQLALCHEMY_DATABASE_URI = config.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TODAY = datetime.date(datetime.now())
    YSTDAY = TODAY - timedelta(days=1)
    SDLY = TODAY - timedelta(days=366)
    SDLY2 = SDLY + timedelta(days=1)
